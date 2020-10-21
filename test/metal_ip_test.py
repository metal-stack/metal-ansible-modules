import sys
from mock import patch
from test import (
    MetalModules,
    AnsibleFailJson,
    AnsibleExitJson,
    set_module_args,
    MODULES_PATH,
)
from metal_python import models

sys.path.insert(0, MODULES_PATH)


class TestMetalIPModule(MetalModules):
    def setUp(self):
        self.defaultSetUpTasks()

        import metal_ip
        self.module = metal_ip

    @patch("metal_python.api.ip_api.IpApi.allocate_ip",
           side_effect=[
               models.V1IPResponse(
                   ipaddress="212.34.89.212",
                   networkid="internet",
                   projectid="12e1b1db-44d7-4f57-9c9d-5799b582ab8f",
                   tags=["ci.metal-stack.io/manager=ansible"])
           ])
    def test_ip_present_random_ip(self, mock):
        set_module_args(
            dict(
                api_url="http://somewhere",
                api_hmac="hmac",
                name="test",
                description="b",
                network="internet",
                project="12e1b1db-44d7-4f57-9c9d-5799b582ab8f",
            )
        )

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        mock.assert_called()
        mock.assert_called_with(
            models.V1IPAllocateRequest(
                description="b",
                name="test",
                networkid="internet",
                projectid="12e1b1db-44d7-4f57-9c9d-5799b582ab8f",
                tags=["ci.metal-stack.io/manager=ansible"],
                type="ephemeral"
            )
        )

        expected = dict(
            ip="212.34.89.212",
            changed=True,
        )
        self.assertDictEqual(result.exception.module_results, expected)

    @patch("metal_python.api.ip_api.IpApi.find_ip",
           side_effect=[
               models.V1IPResponse(
                   ipaddress="212.34.89.212",
                   name="shoot-ip-1",
                   description="b",
                   networkid="internet",
                   projectid="2ada3f21-67fc-4432-a9ba-89b670245456",
                   type="ephemeral",
                   tags=["ci.metal-stack.io/manager=ansible"])
           ])
    def test_ip_present_static_ip_already_exists(self, mocks):
        set_module_args(
            dict(
                api_url="http://somewhere",
                api_hmac="hmac",
                name="shoot-ip-1",
                ip="212.34.89.212",
                description="b",
                network="internet",
                project="2ada3f21-67fc-4432-a9ba-89b670245456"
            )
        )

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        mocks.assert_called()
        mocks.assert_called_with("212.34.89.212")

        expected = dict(
            ip="212.34.89.212",
            changed=False,
        )
        self.assertDictEqual(result.exception.module_results, expected)

    @patch("metal_python.api.ip_api.IpApi.find_ip",
           side_effect=[
               models.V1IPResponse(
                   ipaddress="212.34.89.212",
                   name="shoot-ip-1",
                   description="b",
                   networkid="internet",
                   projectid="2ada3f21-67fc-4432-a9ba-89b670245456",
                   type="ephemeral",
                   tags=["ci.metal-stack.io/manager=ansible"])
           ])
    @patch("metal_python.api.ip_api.IpApi.update_ip",
           side_effect=[
               models.V1IPResponse(
                   ipaddress="212.34.89.212",
                   name="shoot-ip-1",
                   description="b",
                   networkid="internet",
                   projectid="2ada3f21-67fc-4432-a9ba-89b670245456",
                   type="ephemeral",
                   tags=["ci.metal-stack.io/manager=ansible"])
           ])
    def test_ip_present_static_ip_update(self, update_mock, find_mock):
        set_module_args(
            dict(
                api_url="http://somewhere",
                api_hmac="hmac",
                name="shoot-ip-1",
                ip="212.34.89.212",
                description="b",
                network="internet",
                tags=["a-new-tag"],
                project="2ada3f21-67fc-4432-a9ba-89b670245456"
            )
        )

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        find_mock.assert_called()
        find_mock.assert_called_with("212.34.89.212")

        update_mock.assert_called()
        update_mock.assert_called_with(
            models.V1IPUpdateRequest(
                ipaddress="212.34.89.212",
                type="ephemeral",
                tags=["a-new-tag", "ci.metal-stack.io/manager=ansible"],
            )
        )

        expected = dict(
            ip="212.34.89.212",
            changed=True,
        )
        self.assertDictEqual(result.exception.module_results, expected)

    @patch("metal_python.api.ip_api.IpApi.find_ip", side_effect=[None])
    @patch("metal_python.api.ip_api.IpApi.allocate_ip",
           side_effect=[
               models.V1IPResponse(
                   ipaddress="212.34.89.212",
                   networkid="internet",
                   projectid="12e1b1db-44d7-4f57-9c9d-5799b582ab8f",
                   tags=["ci.metal-stack.io/manager=ansible"])
           ])
    def test_ip_present_static_ip_allocate(self, allocate_mock, find_mock):
        set_module_args(
            dict(
                api_url="http://somewhere",
                api_hmac="hmac",
                name="shoot-ip-1",
                ip="212.34.89.212",
                description="b",
                network="internet",
                project="2ada3f21-67fc-4432-a9ba-89b670245456"
            )
        )

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        find_mock.assert_called()
        find_mock.assert_called_with("212.34.89.212")
        allocate_mock.assert_called()
        allocate_mock.assert_called_with(
            models.V1IPAllocateRequest(
                description="b",
                name="shoot-ip-1",
                networkid="internet",
                projectid="2ada3f21-67fc-4432-a9ba-89b670245456",
                type="ephemeral",
                tags=["ci.metal-stack.io/manager=ansible"],
            )
        )

        expected = dict(
            ip="212.34.89.212",
            changed=True,
        )
        self.assertDictEqual(result.exception.module_results, expected)

    @patch("metal_python.api.ip_api.IpApi.find_ip",
           side_effect=[
               models.V1IPResponse(
                   ipaddress="212.34.89.212",
                   networkid="internet",
                   projectid="2ada3f21-67fc-4432-a9ba-89b670245456",
                   tags=["ci.metal-stack.io/manager=ansible"])
           ])
    @patch("metal_python.api.ip_api.IpApi.free_ip",
           side_effect=[
               models.V1IPResponse(
                   ipaddress="212.34.89.212",
                   networkid="internet",
                   projectid="12e1b1db-44d7-4f57-9c9d-5799b582ab8f",
                   tags=["ci.metal-stack.io/manager=ansible"])
           ])
    def test_ip_absent(self, free_mock, find_mock):
        set_module_args(
            dict(
                api_url="http://somewhere",
                api_hmac="hmac",
                ip="212.34.89.212",
                state="absent"
            )
        )
        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        find_mock.assert_called()
        find_mock.assert_called_with("212.34.89.212")
        free_mock.assert_called()
        free_mock.assert_called_with("212.34.89.212")

        expected = dict(
            ip="212.34.89.212",
            changed=True,
        )
        self.assertDictEqual(result.exception.module_results, expected)

    def test_ip_absent_ip_arg_required(self):
        set_module_args(
            dict(
                api_url="http://somewhere",
                api_hmac="hmac",
                state="absent"
            )
        )

        with self.assertRaisesRegex(AnsibleFailJson, "ip is a required argument when state is absent"):
            self.module.main()
