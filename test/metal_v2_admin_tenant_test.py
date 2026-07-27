import sys

from connectrpc.code import Code
from connectrpc.errors import ConnectError
from google.protobuf.json_format import MessageToDict
from google.protobuf import timestamp_pb2

from metalstack.admin.v2 import tenant_pb2 as admin_tenant_pb2
from metalstack.api.v2 import common_pb2, tenant_pb2
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


TENANT_LOGIN = "my-tenant"

FIND_QUERY = admin_tenant_pb2.TenantServiceListRequest(
    query=tenant_pb2.TenantQuery(
        labels=common_pb2.Labels(labels=V2_TEST_COMMON_LABELS),
    ),
)

TEST_TENANT = tenant_pb2.Tenant(
    login=TENANT_LOGIN,
    name="my-tenant",
    description="desc",
    email="test@test.com",
    avatar_url="http://avatar",
    meta=common_pb2.Meta(
        labels=common_pb2.Labels(labels=V2_TEST_COMMON_LABELS),
    ),
)


class TestMetalV2AdminTenantModule(V2MetalModules):
    def setUp(self):
        super().setUp()
        import metal_v2_admin_tenant

        self.module = metal_v2_admin_tenant

    def test_present_create(self):
        self.interceptor = TestClientInterceptor([
            RpcCall(
                request=FIND_QUERY,
                response=admin_tenant_pb2.TenantServiceListResponse(
                    tenants=[]),
            ),
            RpcCall(
                request=admin_tenant_pb2.TenantServiceCreateRequest(
                    name=TEST_TENANT.name,
                    description=TEST_TENANT.description,
                    email=TEST_TENANT.email,
                    avatar_url=TEST_TENANT.avatar_url,
                    labels=common_pb2.Labels(labels=V2_TEST_COMMON_LABELS),
                ),
                response=admin_tenant_pb2.TenantServiceCreateResponse(
                    tenant=TEST_TENANT,
                ),
            ),
        ])

        set_module_args(dict(
            api_url=V2_TEST_API_URL,
            api_token=V2_TEST_API_TOKEN,
            identifier="test",
            name=TEST_TENANT.name,
            description=TEST_TENANT.description,
            email=TEST_TENANT.email,
            avatar_url=TEST_TENANT.avatar_url,
            labels=V2_TEST_COMMON_LABELS,
        ))

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        expected = dict(
            id=TENANT_LOGIN,
            changed=True,
            tenant=MessageToDict(TEST_TENANT),
        )
        self.assertDictEqual(result.exception.module_results, expected)

    def test_present_already_exists(self):
        self.interceptor = TestClientInterceptor([
            RpcCall(
                request=FIND_QUERY,
                response=admin_tenant_pb2.TenantServiceListResponse(
                    tenants=[TEST_TENANT],
                ),
            ),
        ])

        set_module_args(dict(
            api_url=V2_TEST_API_URL,
            api_token=V2_TEST_API_TOKEN,
            identifier="test",
            name=TEST_TENANT.name,
            description=TEST_TENANT.description,
            email=TEST_TENANT.email,
            avatar_url=TEST_TENANT.avatar_url,
            labels=V2_TEST_COMMON_LABELS,
        ))

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        expected = dict(
            id=TENANT_LOGIN,
            changed=False,
            tenant=MessageToDict(TEST_TENANT),
        )
        self.assertDictEqual(result.exception.module_results, expected)

    def test_present_update(self):
        updated_tenant = tenant_pb2.Tenant()
        updated_tenant.CopyFrom(TEST_TENANT)
        updated_tenant.email = "test-updated@test.com"
        updated_tenant.avatar_url = "http://new-avatar"

        self.interceptor = TestClientInterceptor([
            RpcCall(
                request=FIND_QUERY,
                response=admin_tenant_pb2.TenantServiceListResponse(
                    tenants=[TEST_TENANT],
                ),
            ),
            RpcCall(
                request=tenant_pb2.TenantServiceUpdateRequest(
                    login=TENANT_LOGIN,
                    email="test-updated@test.com",
                    avatar_url="http://new-avatar",
                    update_meta=common_pb2.UpdateMeta(
                        updated_at=timestamp_pb2.Timestamp(seconds=0),
                        locking_strategy=common_pb2.OPTIMISTIC_LOCKING_STRATEGY_CLIENT,
                    ),
                ),
                response=tenant_pb2.TenantServiceUpdateResponse(
                    tenant=updated_tenant,
                ),
            ),
        ])

        set_module_args(dict(
            api_url=V2_TEST_API_URL,
            api_token=V2_TEST_API_TOKEN,
            identifier="test",
            name=TEST_TENANT.name,
            description=TEST_TENANT.description,
            email="test-updated@test.com",
            avatar_url="http://new-avatar",
            labels=V2_TEST_COMMON_LABELS,
        ))

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        res = result.exception.module_results
        self.assertEqual(res["changed"], True)
        self.assertEqual(res["id"], TENANT_LOGIN)

    def test_absent_delete(self):
        self.interceptor = TestClientInterceptor([
            RpcCall(
                request=FIND_QUERY,
                response=admin_tenant_pb2.TenantServiceListResponse(
                    tenants=[TEST_TENANT],
                ),
            ),
            RpcCall(
                request=tenant_pb2.TenantServiceDeleteRequest(
                    login=TENANT_LOGIN,
                ),
                response=tenant_pb2.TenantServiceDeleteResponse(
                    tenant=TEST_TENANT,
                ),
            ),
        ])

        set_module_args(dict(
            api_url=V2_TEST_API_URL,
            api_token=V2_TEST_API_TOKEN,
            identifier="test",
            name=TEST_TENANT.name,
            description=TEST_TENANT.description,
            state="absent",
        ))

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        expected = dict(
            id=TENANT_LOGIN,
            changed=True,
            tenant=MessageToDict(TEST_TENANT),
        )
        self.assertDictEqual(result.exception.module_results, expected)

    def test_absent_noop(self):
        self.interceptor = TestClientInterceptor([
            RpcCall(
                request=FIND_QUERY,
                response=admin_tenant_pb2.TenantServiceListResponse(
                    tenants=[]),
            ),
        ])

        set_module_args(dict(
            api_url=V2_TEST_API_URL,
            api_token=V2_TEST_API_TOKEN,
            identifier="test",
            name=TEST_TENANT.name,
            description=TEST_TENANT.description,
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
            name=TEST_TENANT.name,
            description=TEST_TENANT.description,
        ))

        with self.assertRaises(AnsibleFailJson) as result:
            self.module.main()

        self.assertTrue(result.exception.module_results.get("failed"))
        self.assertEqual("request to metal-apiserver failed",
                         result.exception.module_results.get("msg"))

    def test_missing_auth(self):
        set_module_args(dict(
            identifier="test",
            name=TEST_TENANT.name,
            description=TEST_TENANT.description,
        ))

        with self.assertRaises(Exception) as result:
            self.module.main()

        self.assertEqual(
            "api_url or METAL_APIV2_URL must be provided", str(result.exception))
