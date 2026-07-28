import sys

from connectrpc.code import Code
from connectrpc.errors import ConnectError
from google.protobuf.json_format import MessageToDict
from google.protobuf import timestamp_pb2

from metalstack.admin.v2 import token_pb2 as admin_token_pb2
from metalstack.api.v2 import common_pb2, token_pb2
from test import (
    V2MetalModules,
    AnsibleExitJson,
    AnsibleFailJson,
    set_module_args,
    MODULES_PATH,
    V2_TEST_COMMON_LABELS,
    V2_TEST_API_URL,
    V2_TEST_API_TOKEN,
)
from metalstack.client.test_interceptor import TestClientInterceptor, RpcCall

sys.path.insert(0, MODULES_PATH)


TOKEN_UUID = "ae6834bd-1ca8-4d22-b38a-8a7c771c06b0"
TOKEN_SECRET = "jwt-secret-value"

FIND_QUERY = admin_token_pb2.TokenServiceListRequest(
    query=token_pb2.TokenQuery(
        labels=common_pb2.Labels(labels=V2_TEST_COMMON_LABELS),
    ),
)

TEST_TOKEN = token_pb2.Token(
    uuid=TOKEN_UUID,
    user="metal-bmc",
    description="an infra component token",
    token_type=token_pb2.TOKEN_TYPE_API,
    admin_role=common_pb2.ADMIN_ROLE_EDITOR,
    project_roles={"pj-1": common_pb2.PROJECT_ROLE_EDITOR},
    tenant_roles={"tn-1": common_pb2.TENANT_ROLE_VIEWER},
    permissions=[
        token_pb2.MethodPermission(
            methods=["/metalstack.api.v2.TokenService/Refresh"], subject="self"),
    ],
    meta=common_pb2.Meta(
        labels=common_pb2.Labels(labels=V2_TEST_COMMON_LABELS),
    ),
)


class TestMetalV2AdminTokenModule(V2MetalModules):
    def setUp(self):
        super().setUp()
        import metal_v2_admin_token

        self.module = metal_v2_admin_token

    def test_present_create(self):
        self.interceptor = TestClientInterceptor([
            RpcCall(
                request=FIND_QUERY,
                response=admin_token_pb2.TokenServiceListResponse(tokens=[]),
            ),
            RpcCall(
                request=admin_token_pb2.TokenServiceCreateRequest(
                    user=TEST_TOKEN.user,
                    token_create_request=token_pb2.TokenServiceCreateRequest(
                        description=TEST_TOKEN.description,
                        labels=common_pb2.Labels(labels=V2_TEST_COMMON_LABELS),
                        admin_role="ADMIN_ROLE_EDITOR",
                        permissions=[
                            token_pb2.PermissionsByVisibility(
                                self=token_pb2.SelfPermissions(
                                    methods=[
                                        "/metalstack.api.v2.TokenService/Refresh"],
                                ),
                            ),
                        ],
                        project_roles={
                            "pj-1": common_pb2.PROJECT_ROLE_EDITOR,
                        },
                        tenant_roles={
                            "tn-1": common_pb2.TENANT_ROLE_VIEWER,
                        },
                    ),
                ),
                response=admin_token_pb2.TokenServiceCreateResponse(
                    token=TEST_TOKEN,
                    secret=TOKEN_SECRET,
                ),
            ),
        ])

        set_module_args(dict(
            api_url=V2_TEST_API_URL,
            api_token=V2_TEST_API_TOKEN,
            identifier="test",
            user=TEST_TOKEN.user,
            description=TEST_TOKEN.description,
            labels=V2_TEST_COMMON_LABELS,
            admin_role="ADMIN_ROLE_EDITOR",
            permissions=[
                {"self": {"methods": [
                    "/metalstack.api.v2.TokenService/Refresh"]}},
            ],
            project_roles=[
                {"id": "pj-1", "role": "PROJECT_ROLE_EDITOR"},
            ],
            tenant_roles=[
                {"id": "tn-1", "role": "TENANT_ROLE_VIEWER"},
            ],
        ))

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        res = result.exception.module_results
        self.assertEqual(res["changed"], True)
        self.assertEqual(res["id"], TOKEN_UUID)
        self.assertEqual(res.get("secret"), TOKEN_SECRET)

    def test_present_already_exists(self):
        self.interceptor = TestClientInterceptor([
            RpcCall(
                request=FIND_QUERY,
                response=admin_token_pb2.TokenServiceListResponse(
                    tokens=[TEST_TOKEN],
                ),
            ),
        ])

        set_module_args(dict(
            api_url=V2_TEST_API_URL,
            api_token=V2_TEST_API_TOKEN,
            identifier="test",
            user=TEST_TOKEN.user,
            description=TEST_TOKEN.description,
            labels=V2_TEST_COMMON_LABELS,
            admin_role="ADMIN_ROLE_EDITOR",
            permissions=[
                {"self": {"methods": [
                    "/metalstack.api.v2.TokenService/Refresh"]}},
            ],
            project_roles=[
                {"id": "pj-1", "role": "PROJECT_ROLE_EDITOR"},
            ],
            tenant_roles=[
                {"id": "tn-1", "role": "TENANT_ROLE_VIEWER"},
            ],
            use_latest_identifier=True,
            api_timeout=60,
        ))

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        res = result.exception.module_results
        self.assertEqual(res["changed"], False)
        self.assertEqual(res["id"], TOKEN_UUID)

    def test_present_use_latest_identifier(self):
        older_uuid = "00000000-0000-0000-0000-000000000001"
        older = token_pb2.Token()
        older.CopyFrom(TEST_TOKEN)
        older.uuid = older_uuid
        older.meta.created_at.CopyFrom(timestamp_pb2.Timestamp(seconds=100))

        newer = token_pb2.Token()
        newer.CopyFrom(TEST_TOKEN)
        newer.meta.created_at.CopyFrom(timestamp_pb2.Timestamp(seconds=200))

        self.interceptor = TestClientInterceptor([
            RpcCall(
                request=FIND_QUERY,
                response=admin_token_pb2.TokenServiceListResponse(
                    tokens=[older, newer],
                ),
            ),
        ])

        set_module_args(dict(
            api_url=V2_TEST_API_URL,
            api_token=V2_TEST_API_TOKEN,
            identifier="test",
            user=TEST_TOKEN.user,
            description=TEST_TOKEN.description,
            labels=V2_TEST_COMMON_LABELS,
            admin_role="ADMIN_ROLE_EDITOR",
            permissions=[
                {"self": {"methods": ["/metalstack.api.v2.TokenService/Refresh"]}},
            ],
            project_roles=[
                {"id": "pj-1", "role": "PROJECT_ROLE_EDITOR"},
            ],
            tenant_roles=[
                {"id": "tn-1", "role": "TENANT_ROLE_VIEWER"},
            ],
            use_latest_identifier=True,
        ))

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        res = result.exception.module_results
        self.assertEqual(res["changed"], False)
        self.assertEqual(res["id"], TOKEN_UUID)

    def test_present_update(self):
        existing = token_pb2.Token()
        existing.CopyFrom(TEST_TOKEN)
        existing.description = "old description"

        updated = token_pb2.Token()
        updated.CopyFrom(existing)
        updated.description = "new description"

        self.interceptor = TestClientInterceptor([
            RpcCall(
                request=FIND_QUERY,
                response=admin_token_pb2.TokenServiceListResponse(
                    tokens=[existing],
                ),
            ),
            RpcCall(
                request=token_pb2.TokenServiceUpdateRequest(
                    uuid=TOKEN_UUID,
                    description=updated.description,
                    update_meta=common_pb2.UpdateMeta(),
                ),
                response=token_pb2.TokenServiceUpdateResponse(
                    token=updated,
                ),
            ),
        ])

        set_module_args(dict(
            api_url=V2_TEST_API_URL,
            api_token=V2_TEST_API_TOKEN,
            identifier="test",
            user=TEST_TOKEN.user,
            description=updated.description,
            labels=V2_TEST_COMMON_LABELS,
            admin_role="ADMIN_ROLE_EDITOR",
            permissions=[
                {"self": {"methods": [
                    "/metalstack.api.v2.TokenService/Refresh"]}},
            ],
            project_roles=[
                {"id": "pj-1", "role": "PROJECT_ROLE_EDITOR"},
            ],
            tenant_roles=[
                {"id": "tn-1", "role": "TENANT_ROLE_VIEWER"},
            ],
        ))

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        expected = dict(
            changed=True,
            id=TOKEN_UUID,
            token=MessageToDict(updated),
        )
        self.assertDictEqual(result.exception.module_results, expected)

    def test_absent_revoke(self):
        self.interceptor = TestClientInterceptor([
            RpcCall(
                request=FIND_QUERY,
                response=admin_token_pb2.TokenServiceListResponse(
                    tokens=[TEST_TOKEN],
                ),
            ),
            RpcCall(
                request=admin_token_pb2.TokenServiceRevokeRequest(
                    user=TEST_TOKEN.user,
                    uuid=TOKEN_UUID,
                ),
                response=admin_token_pb2.TokenServiceRevokeResponse(),
            ),
        ])

        set_module_args(dict(
            api_url=V2_TEST_API_URL,
            api_token=V2_TEST_API_TOKEN,
            identifier="test",
            user=TEST_TOKEN.user,
            state="absent",
        ))

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        res = result.exception.module_results
        self.assertEqual(res["changed"], True)

    def test_absent_noop(self):
        self.interceptor = TestClientInterceptor([
            RpcCall(
                request=FIND_QUERY,
                response=admin_token_pb2.TokenServiceListResponse(tokens=[]),
            ),
        ])

        set_module_args(dict(
            api_url=V2_TEST_API_URL,
            api_token=V2_TEST_API_TOKEN,
            identifier="test",
            user=TEST_TOKEN.user,
            state="absent",
        ))

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        self.assertEqual(result.exception.module_results["changed"], False)

    def test_find_error(self):
        self.interceptor = TestClientInterceptor([
            RpcCall(
                request=FIND_QUERY,
                error=ConnectError(
                    code=Code.UNAVAILABLE,
                    message="service unavailable",
                ),
            ),
        ])

        set_module_args(dict(
            api_url=V2_TEST_API_URL,
            api_token=V2_TEST_API_TOKEN,
            identifier="test",
            user=TEST_TOKEN.user,
            description=TEST_TOKEN.description,
        ))

        with self.assertRaises(AnsibleFailJson) as result:
            self.module.main()

        self.assertTrue(result.exception.module_results.get("failed"))
        self.assertEqual("request to metal-apiserver failed",
                         result.exception.module_results.get("msg"))

    def test_missing_auth(self):
        set_module_args(dict(
            identifier="test",
            user=TEST_TOKEN.user,
            description=TEST_TOKEN.description,
        ))

        with self.assertRaises(Exception) as result:
            self.module.main()

        self.assertEqual(
            "api_url or METAL_APIV2_URL must be provided", str(result.exception))
