import sys

from connectrpc.code import Code
from connectrpc.errors import ConnectError
from google.protobuf.json_format import MessageToDict
from google.protobuf import timestamp_pb2

from metalstack.api.v2 import common_pb2, project_pb2
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


PROJECT_UUID = "3e977e81-6ab5-4f28-b608-e7e94d62efb7"

FIND_QUERY = project_pb2.ProjectServiceListRequest(
    query=project_pb2.ProjectQuery(
        labels=common_pb2.Labels(labels=V2_TEST_COMMON_LABELS),
    ),
)

TEST_PROJECT = project_pb2.Project(
    uuid=PROJECT_UUID,
    name="my-project",
    description="desc",
    tenant="tenant-a",
    avatar_url="http://avatar",
    meta=common_pb2.Meta(
        labels=common_pb2.Labels(labels=V2_TEST_COMMON_LABELS),
    ),
)


class TestMetalV2AdminProjectModule(V2MetalModules):
    def setUp(self):
        super().setUp()
        import metal_v2_admin_project

        self.module = metal_v2_admin_project

    def test_present_create(self):
        self.interceptor = TestClientInterceptor([
            RpcCall(
                request=FIND_QUERY,
                response=project_pb2.ProjectServiceListResponse(projects=[]),
            ),
            RpcCall(
                request=project_pb2.ProjectServiceCreateRequest(
                    login=TEST_PROJECT.tenant,
                    name=TEST_PROJECT.name,
                    description=TEST_PROJECT.description,
                    avatar_url=TEST_PROJECT.avatar_url,
                    labels=common_pb2.Labels(labels=V2_TEST_COMMON_LABELS),
                ),
                response=project_pb2.ProjectServiceCreateResponse(
                    project=TEST_PROJECT,
                ),
            ),
        ])

        set_module_args(dict(
            api_url=V2_TEST_API_URL,
            api_token=V2_TEST_API_TOKEN,
            identifier="test",
            name=TEST_PROJECT.name,
            tenant=TEST_PROJECT.tenant,
            description=TEST_PROJECT.description,
            avatar_url=TEST_PROJECT.avatar_url,
            labels=V2_TEST_COMMON_LABELS,
        ))

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        expected = dict(
            id=PROJECT_UUID,
            changed=True,
            project=MessageToDict(TEST_PROJECT),
        )
        self.assertDictEqual(result.exception.module_results, expected)

    def test_present_already_exists(self):
        self.interceptor = TestClientInterceptor([
            RpcCall(
                request=FIND_QUERY,
                response=project_pb2.ProjectServiceListResponse(
                    projects=[TEST_PROJECT],
                ),
            ),
        ])

        set_module_args(dict(
            api_url=V2_TEST_API_URL,
            api_token=V2_TEST_API_TOKEN,
            identifier="test",
            name=TEST_PROJECT.name,
            tenant=TEST_PROJECT.tenant,
            description=TEST_PROJECT.description,
            avatar_url=TEST_PROJECT.avatar_url,
            labels=V2_TEST_COMMON_LABELS,
        ))

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        expected = dict(
            id=PROJECT_UUID,
            changed=False,
            project=MessageToDict(TEST_PROJECT),
        )
        self.assertDictEqual(result.exception.module_results, expected)

    def test_present_update(self):
        updated_project = project_pb2.Project()
        updated_project.CopyFrom(TEST_PROJECT)
        updated_project.name = "my-project-updated"

        self.interceptor = TestClientInterceptor([
            RpcCall(
                request=FIND_QUERY,
                response=project_pb2.ProjectServiceListResponse(
                    projects=[TEST_PROJECT],
                ),
            ),
            RpcCall(
                request=project_pb2.ProjectServiceUpdateRequest(
                    project=PROJECT_UUID,
                    name="my-project-updated",
                    labels=common_pb2.UpdateLabels(
                        replace=common_pb2.Labels(
                            labels=V2_TEST_COMMON_LABELS | {"foo": "bar"},
                        ),
                    ),
                    update_meta=common_pb2.UpdateMeta(
                        updated_at=timestamp_pb2.Timestamp(seconds=0),
                        locking_strategy=common_pb2.OPTIMISTIC_LOCKING_STRATEGY_CLIENT,
                    ),
                ),
                response=project_pb2.ProjectServiceUpdateResponse(
                    project=updated_project,
                ),
            ),
        ])

        set_module_args(dict(
            api_url=V2_TEST_API_URL,
            api_token=V2_TEST_API_TOKEN,
            identifier="test",
            name="my-project-updated",
            tenant=TEST_PROJECT.tenant,
            description=TEST_PROJECT.description,
            avatar_url=TEST_PROJECT.avatar_url,
            labels=V2_TEST_COMMON_LABELS | {"foo": "bar"},
        ))

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        res = result.exception.module_results
        self.assertEqual(res["changed"], True)
        self.assertEqual(res["id"], PROJECT_UUID)

    def test_absent_delete(self):
        self.interceptor = TestClientInterceptor([
            RpcCall(
                request=FIND_QUERY,
                response=project_pb2.ProjectServiceListResponse(
                    projects=[TEST_PROJECT],
                ),
            ),
            RpcCall(
                request=project_pb2.ProjectServiceDeleteRequest(
                    project=PROJECT_UUID,
                ),
                response=project_pb2.ProjectServiceDeleteResponse(
                    project=TEST_PROJECT,
                ),
            ),
        ])

        set_module_args(dict(
            api_url=V2_TEST_API_URL,
            api_token=V2_TEST_API_TOKEN,
            identifier="test",
            name=TEST_PROJECT.name,
            tenant=TEST_PROJECT.tenant,
            description=TEST_PROJECT.description,
            state="absent",
        ))

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        expected = dict(
            id=PROJECT_UUID,
            changed=True,
            project=MessageToDict(TEST_PROJECT),
        )
        self.assertDictEqual(result.exception.module_results, expected)

    def test_absent_noop(self):
        self.interceptor = TestClientInterceptor([
            RpcCall(
                request=FIND_QUERY,
                response=project_pb2.ProjectServiceListResponse(projects=[]),
            ),
        ])

        set_module_args(dict(
            api_url=V2_TEST_API_URL,
            api_token=V2_TEST_API_TOKEN,
            identifier="test",
            name=TEST_PROJECT.name,
            tenant=TEST_PROJECT.tenant,
            description=TEST_PROJECT.description,
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
            name=TEST_PROJECT.name,
            tenant=TEST_PROJECT.tenant,
            description=TEST_PROJECT.description,
        ))

        with self.assertRaises(AnsibleFailJson) as result:
            self.module.main()

        self.assertTrue(result.exception.module_results.get("failed"))
        self.assertEqual("request to metal-apiserver failed",
                         result.exception.module_results.get("msg"))

    def test_missing_auth(self):
        set_module_args(dict(
            identifier="test",
            name=TEST_PROJECT.name,
            tenant=TEST_PROJECT.tenant,
            description=TEST_PROJECT.description,
        ))

        with self.assertRaises(Exception) as result:
            self.module.main()

        self.assertEqual(
            "api_url or METAL_APIV2_URL must be provided", str(result.exception))
