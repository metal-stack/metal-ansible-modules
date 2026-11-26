import sys

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
from google.protobuf import timestamp_pb2
from google.protobuf.json_format import MessageToDict
from connectrpc.errors import ConnectError
from connectrpc.code import Code

from metalstack.api.v2 import common_pb2, ip_pb2

sys.path.insert(0, MODULES_PATH)

IP_UUID = "9f9e6a0c-1a4e-4a8b-a3c2-5d3c7e0f4b11"
PROJECT_UUID = "3e977e81-6ab5-4f28-b608-e7e94d62efb7"

FIND_QUERY = ip_pb2.IPServiceListRequest(
    project=PROJECT_UUID,
    query=ip_pb2.IPQuery(
        labels=common_pb2.Labels(labels=V2_TEST_COMMON_LABELS),
    ),
)

TEST_IP = ip_pb2.IP(
    uuid=IP_UUID,
    ip="203.0.113.10",
    name="my-ip",
    description="desc",
    network="internet",
    project=PROJECT_UUID,
    type=ip_pb2.IP_TYPE_STATIC,
    meta=common_pb2.Meta(
        created_at=None,
        updated_at=None,
        labels=common_pb2.Labels(labels=V2_TEST_COMMON_LABELS),
    ),
)

BASE_ARGS = dict(
    api_url=V2_TEST_API_URL,
    api_token=V2_TEST_API_TOKEN,
    identifier="test",
    project=PROJECT_UUID,
)

PRESENT_ARGS = BASE_ARGS | dict(
    name=TEST_IP.name,
    description=TEST_IP.description,
    network=TEST_IP.network,
    type="static",
    labels=V2_TEST_COMMON_LABELS,
)


class TestMetalV2IPModule(V2MetalModules):
    def setUp(self):
        super().setUp()
        import metal_v2_ip

        self.module = metal_v2_ip

    def _expected(self, ip, changed):
        return dict(
            id=ip.uuid,
            address=ip.ip,
            changed=changed,
            ip=MessageToDict(ip),
        )

    def test_present_create(self):
        self.interceptor = TestClientInterceptor([
            RpcCall(
                request=FIND_QUERY,
                response=ip_pb2.IPServiceListResponse(ips=[]),
            ),
            RpcCall(
                request=ip_pb2.IPServiceCreateRequest(
                    project=PROJECT_UUID,
                    network=TEST_IP.network,
                    name=TEST_IP.name,
                    description=TEST_IP.description,
                    type=ip_pb2.IP_TYPE_STATIC,
                    labels=common_pb2.Labels(labels=V2_TEST_COMMON_LABELS),
                ),
                response=ip_pb2.IPServiceCreateResponse(ip=TEST_IP),
            ),
        ])

        set_module_args(PRESENT_ARGS)

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        self.assertDictEqual(result.exception.module_results,
                             self._expected(TEST_IP, True))

    def test_present_create_specific_ip(self):
        self.interceptor = TestClientInterceptor([
            RpcCall(
                request=FIND_QUERY,
                response=ip_pb2.IPServiceListResponse(ips=[]),
            ),
            RpcCall(
                request=ip_pb2.IPServiceCreateRequest(
                    project=PROJECT_UUID,
                    network=TEST_IP.network,
                    ip=TEST_IP.ip,
                    type=ip_pb2.IP_TYPE_EPHEMERAL,
                    address_family=ip_pb2.IP_ADDRESS_FAMILY_V4,
                    labels=common_pb2.Labels(labels=V2_TEST_COMMON_LABELS),
                ),
                response=ip_pb2.IPServiceCreateResponse(ip=TEST_IP),
            ),
        ])

        set_module_args(BASE_ARGS | dict(
            network=TEST_IP.network,
            ip=TEST_IP.ip,
            address_family="ipv4",
        ))

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        self.assertDictEqual(result.exception.module_results,
                             self._expected(TEST_IP, True))

    def test_present_already_exists(self):
        self.interceptor = TestClientInterceptor([
            RpcCall(
                request=FIND_QUERY,
                response=ip_pb2.IPServiceListResponse(ips=[TEST_IP]),
            ),
        ])

        set_module_args(PRESENT_ARGS)

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        self.assertDictEqual(result.exception.module_results,
                             self._expected(TEST_IP, False))

    def test_present_update(self):
        updated_ip = ip_pb2.IP()
        updated_ip.CopyFrom(TEST_IP)
        updated_ip.name = "my-ip-updated"
        updated_ip.description = "updated desc"
        updated_ip.type = ip_pb2.IP_TYPE_EPHEMERAL
        updated_ip.meta.labels.labels["a"] = "b"

        self.interceptor = TestClientInterceptor([
            RpcCall(
                request=FIND_QUERY,
                response=ip_pb2.IPServiceListResponse(ips=[TEST_IP]),
            ),
            RpcCall(
                request=ip_pb2.IPServiceUpdateRequest(
                    ip=TEST_IP.ip,
                    project=PROJECT_UUID,
                    name=updated_ip.name,
                    description=updated_ip.description,
                    type=ip_pb2.IP_TYPE_EPHEMERAL,
                    labels=common_pb2.UpdateLabels(
                        replace=common_pb2.Labels(
                            labels=V2_TEST_COMMON_LABELS | {"a": "b"}),
                    ),
                    update_meta=common_pb2.UpdateMeta(
                        updated_at=timestamp_pb2.Timestamp(seconds=0),
                        locking_strategy=common_pb2.OPTIMISTIC_LOCKING_STRATEGY_CLIENT,
                    ),
                ),
                response=ip_pb2.IPServiceUpdateResponse(ip=updated_ip),
            ),
        ])

        set_module_args(PRESENT_ARGS | dict(
            name=updated_ip.name,
            description=updated_ip.description,
            type="ephemeral",
            labels={"a": "b"},
        ))

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        self.assertDictEqual(result.exception.module_results,
                             self._expected(updated_ip, True))

    def test_present_update_address_change_fails(self):
        self.interceptor = TestClientInterceptor([
            RpcCall(
                request=FIND_QUERY,
                response=ip_pb2.IPServiceListResponse(ips=[TEST_IP]),
            ),
        ])

        set_module_args(PRESENT_ARGS | dict(ip="203.0.113.11"))

        with self.assertRaises(AnsibleFailJson) as result:
            self.module.main()

        self.assertEqual(
            "ip has address 203.0.113.10, it cannot be changed to 203.0.113.11",
            result.exception.module_results.get("msg"))

    def test_present_update_network_change_fails(self):
        self.interceptor = TestClientInterceptor([
            RpcCall(
                request=FIND_QUERY,
                response=ip_pb2.IPServiceListResponse(ips=[TEST_IP]),
            ),
        ])

        set_module_args(PRESENT_ARGS | dict(network="other"))

        with self.assertRaises(AnsibleFailJson) as result:
            self.module.main()

        self.assertEqual(
            "ip belongs to network internet, it cannot be changed to network other",
            result.exception.module_results.get("msg"))

    def test_present_requires_network(self):
        set_module_args(BASE_ARGS)

        with self.assertRaises(AnsibleFailJson) as result:
            self.module.main()

        self.assertIn("network", result.exception.module_results.get("msg"))

    def test_absent_delete(self):
        self.interceptor = TestClientInterceptor([
            RpcCall(
                request=FIND_QUERY,
                response=ip_pb2.IPServiceListResponse(ips=[TEST_IP]),
            ),
            RpcCall(
                request=ip_pb2.IPServiceDeleteRequest(
                    ip=TEST_IP.ip,
                    project=PROJECT_UUID,
                ),
                response=ip_pb2.IPServiceDeleteResponse(ip=TEST_IP),
            ),
        ])

        set_module_args(BASE_ARGS | dict(state="absent"))

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        self.assertDictEqual(result.exception.module_results,
                             self._expected(TEST_IP, True))

    def test_absent_noop(self):
        self.interceptor = TestClientInterceptor([
            RpcCall(
                request=FIND_QUERY,
                response=ip_pb2.IPServiceListResponse(ips=[]),
            ),
        ])

        set_module_args(BASE_ARGS | dict(state="absent"))

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        expected = dict(
            changed=False,
            id=None,
            address=None,
        )
        self.assertDictEqual(result.exception.module_results, expected)

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

        set_module_args(PRESENT_ARGS)

        with self.assertRaises(AnsibleFailJson) as result:
            self.module.main()

        self.assertTrue(result.exception.module_results.get("failed"))
        self.assertEqual("request to metal-apiserver failed",
                         result.exception.module_results.get("msg"))

    def test_missing_auth(self):
        set_module_args(dict(
            identifier="test",
            project=PROJECT_UUID,
            network=TEST_IP.network,
        ))

        with self.assertRaises(Exception) as result:
            self.module.main()

        self.assertEqual(
            "api_url or METAL_APIV2_URL must be provided", str(result.exception))
