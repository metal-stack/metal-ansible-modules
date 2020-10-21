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


class TestMetalNetworkModule(MetalModules):
    def setUp(self):
        self.defaultSetUpTasks()

        import metal_network
        self.module = metal_network

    def test_module_fail_when_required_args_missing(self):
        set_module_args(dict(
            api_url="http://somewhere",
            api_hmac="hmac",
        ))
        with self.assertRaisesRegex(AnsibleFailJson,
                                    "{'msg': 'either id or partition, project and name must be given', 'failed': True}"):
            self.module.main()

    @patch("metal_python.api.network_api.NetworkApi.find_networks",
           side_effect=[
               [
                   models.V1NetworkResponse(id="02cc0b42-f675-4c7d-a671-f7a9c8214b61",
                                            name="test",
                                            description="b",
                                            prefixes=['10.0.156.0/22'],
                                            projectid="12e1b1db-44d7-4f57-9c9d-5799b582ab8f",
                                            destinationprefixes=["0.0.0.0/0"],
                                            nat=True,
                                            parentnetworkid="parent",
                                            privatesuper=False,
                                            underlay=False,
                                            labels={"ci.metal-stack.io/manager": "ansible"},
                                            usage=models.V1NetworkUsage(
                                                available_ips=10,
                                                available_prefixes=1,
                                                used_ips=1,
                                                used_prefixes=1,
                                            ))
               ]
           ])
    def test_network_present_already_exists(self, mocks):
        set_module_args(
            dict(
                api_url="http://somewhere",
                api_hmac="hmac",
                name="test",
                description="b",
                partition="fra-equ01",
                project="12e1b1db-44d7-4f57-9c9d-5799b582ab8f"
            )
        )

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        mocks.assert_called()
        mocks.assert_called_with(models.V1NetworkFindRequest(
            partitionid="fra-equ01",
            projectid="12e1b1db-44d7-4f57-9c9d-5799b582ab8f",
            name="test",
        ))

        expected = dict(
            id="02cc0b42-f675-4c7d-a671-f7a9c8214b61",
            prefixes=['10.0.156.0/22'],
            changed=False,
        )
        self.assertDictEqual(result.exception.module_results, expected)

    @patch("metal_python.api.network_api.NetworkApi.find_networks",
           side_effect=[
               [
                   models.V1NetworkResponse(id="02cc0b42-f675-4c7d-a671-f7a9c8214b61",
                                            name="test",
                                            description="b",
                                            prefixes=['10.0.156.0/22'],
                                            projectid="12e1b1db-44d7-4f57-9c9d-5799b582ab8f",
                                            destinationprefixes=["0.0.0.0/0"],
                                            nat=True,
                                            parentnetworkid="parent",
                                            privatesuper=False,
                                            underlay=False,
                                            labels={"ci.metal-stack.io/manager": "ansible"},
                                            usage=models.V1NetworkUsage(
                                                available_ips=10,
                                                available_prefixes=1,
                                                used_ips=1,
                                                used_prefixes=1,
                                            ))
               ]
           ])
    @patch("metal_python.api.network_api.NetworkApi.update_network",
           side_effect=[
               models.V1NetworkResponse(id="02cc0b42-f675-4c7d-a671-f7a9c8214b61",
                                        name="new-name",
                                        description="new",
                                        prefixes=['10.0.156.0/22'],
                                        projectid="12e1b1db-44d7-4f57-9c9d-5799b582ab8f",
                                        destinationprefixes=["0.0.0.0/0"],
                                        nat=True,
                                        parentnetworkid="parent",
                                        privatesuper=False,
                                        underlay=False,
                                        labels={"ci.metal-stack.io/manager": "ansible"},
                                        usage=models.V1NetworkUsage(
                                            available_ips=10,
                                            available_prefixes=1,
                                            used_ips=1,
                                            used_prefixes=1,
                                        ))
           ])
    def test_network_present_update(self, update_mock, find_mock):
        set_module_args(
            dict(
                api_url="http://somewhere",
                api_hmac="hmac",
                name="test",
                description="new",
                partition="fra-equ01",
                project="12e1b1db-44d7-4f57-9c9d-5799b582ab8f"
            )
        )

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        find_mock.assert_called()
        find_mock.assert_called_with(models.V1NetworkFindRequest(
            partitionid="fra-equ01",
            projectid="12e1b1db-44d7-4f57-9c9d-5799b582ab8f",
            name="test",
        ))
        update_mock.assert_called()
        update_mock.assert_called_with(models.V1NetworkUpdateRequest(
            id="02cc0b42-f675-4c7d-a671-f7a9c8214b61",
            description="new",
        ))

        expected = dict(
            id="02cc0b42-f675-4c7d-a671-f7a9c8214b61",
            prefixes=['10.0.156.0/22'],
            changed=True,
        )
        self.assertDictEqual(result.exception.module_results, expected)

    @patch("metal_python.api.network_api.NetworkApi.find_networks",
           side_effect=[[]])
    @patch("metal_python.api.network_api.NetworkApi.allocate_network",
           side_effect=[
               models.V1NetworkResponse(id="a-uuid",
                                        prefixes=['10.0.0.0/22'],
                                        projectid="12e1b1db-44d7-4f57-9c9d-5799b582ab8f",
                                        destinationprefixes=["0.0.0.0/0"],
                                        nat=True,
                                        parentnetworkid="parent",
                                        privatesuper=False,
                                        underlay=False,
                                        labels={"ci.metal-stack.io/manager": "ansible"},
                                        usage=models.V1NetworkUsage(
                                            available_ips=10,
                                            available_prefixes=1,
                                            used_ips=1,
                                            used_prefixes=1,
                                        ))
           ])
    def test_network_present_allocate(self, allocate_mock, find_mock):
        set_module_args(
            dict(
                api_url="http://somewhere",
                api_hmac="hmac",
                name="test2",
                description="b",
                partition="fra-equ01",
                project="a-uuid"
            )
        )

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        find_mock.assert_called()
        find_mock.assert_called_with(models.V1NetworkFindRequest(
            partitionid="fra-equ01",
            projectid="a-uuid",
            name="test2",
        ))
        allocate_mock.assert_called()
        allocate_mock.assert_called_with(models.V1NetworkAllocateRequest(
            name="test2",
            partitionid="fra-equ01",
            description="b",
            projectid="a-uuid",
            labels={"ci.metal-stack.io/manager": "ansible"},
        ))

        expected = dict(
            id="a-uuid",
            prefixes=["10.0.0.0/22"],
            changed=True,
        )
        self.assertDictEqual(result.exception.module_results, expected)

    @patch("metal_python.api.network_api.NetworkApi.find_networks",
           side_effect=[
               [
                   models.V1NetworkResponse(id="02cc0b42-f675-4c7d-a671-f7a9c8214b61",
                                            prefixes=['10.0.156.0/22'],
                                            projectid="12e1b1db-44d7-4f57-9c9d-5799b582ab8f",
                                            destinationprefixes=["0.0.0.0/0"],
                                            nat=True,
                                            parentnetworkid="parent",
                                            privatesuper=False,
                                            underlay=False,
                                            labels={"ci.metal-stack.io/manager": "ansible"},
                                            usage=models.V1NetworkUsage(
                                                available_ips=10,
                                                available_prefixes=1,
                                                used_ips=1,
                                                used_prefixes=1,
                                            ))
               ]
           ])
    @patch("metal_python.api.network_api.NetworkApi.free_network",
           side_effect=[
               models.V1NetworkResponse(id="02cc0b42-f675-4c7d-a671-f7a9c8214b61",
                                        prefixes=['10.0.156.0/22'],
                                        projectid="12e1b1db-44d7-4f57-9c9d-5799b582ab8f",
                                        destinationprefixes=["0.0.0.0/0"],
                                        nat=True,
                                        parentnetworkid="parent",
                                        privatesuper=False,
                                        underlay=False,
                                        labels={"ci.metal-stack.io/manager": "ansible"},
                                        usage=models.V1NetworkUsage(
                                            available_ips=10,
                                            available_prefixes=1,
                                            used_ips=1,
                                            used_prefixes=1,
                                        ))
           ])
    def test_network_absent(self, free_mock, find_mock):
        set_module_args(
            dict(
                api_url="http://somewhere",
                api_hmac="hmac",
                name="test",
                partition="fra-equ01",
                project="12e1b1db-44d7-4f57-9c9d-5799b582ab8f",
                state="absent"
            )
        )

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        find_mock.assert_called()
        find_mock.assert_called_with(models.V1NetworkFindRequest(
            partitionid="fra-equ01",
            projectid="12e1b1db-44d7-4f57-9c9d-5799b582ab8f",
            name="test",
        ))
        free_mock.assert_called()
        free_mock.assert_called_with("02cc0b42-f675-4c7d-a671-f7a9c8214b61")

        expected = dict(
            id="02cc0b42-f675-4c7d-a671-f7a9c8214b61",
            prefixes=["10.0.156.0/22"],
            changed=True,
        )
        self.assertDictEqual(result.exception.module_results, expected)
