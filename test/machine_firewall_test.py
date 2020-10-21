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


class TestMetalFirewallModule(MetalModules):
    def setUp(self):
        self.defaultSetUpTasks()

        import metal_firewall
        self.module = metal_firewall

    def test_module_fail_when_required_args_missing(self):
        set_module_args(dict(
            api_url="http://somewhere",
            api_hmac="hmac",
        ))
        with self.assertRaisesRegex(AnsibleFailJson,
                                    "{'msg': 'missing required arguments: project', 'failed': True}"):
            self.module.main()

    def test_module_fail_when_required_args_missing_no_id_or_name(self):
        set_module_args(dict(
            api_url="http://somewhere",
            api_hmac="hmac",
            project="a-project",
        ))
        with self.assertRaisesRegex(AnsibleFailJson,
                                    "{'msg': 'either id or name must be given', 'failed': True}"):
            self.module.main()

    @patch("metal_python.api.firewall_api.FirewallApi.find_firewalls",
           side_effect=[
               [
                   models.V1FirewallResponse(
                       id="5345b85e-9841-4699-b20e-0efaa806b690",
                       bios=models.V1MachineBIOS(
                           _date="",
                           vendor="",
                           version="",
                       ),
                       events=[],
                       hardware=models.V1MachineHardware(
                           cpu_cores=4,
                           disks=[],
                           memory=1024,
                           nics=[],
                       ),
                       ledstate="",
                       liveliness="Alive",
                       state="",
                       tags=["ci.metal-stack.io/manager=ansible"],
                       allocation=models.V1MachineAllocation(
                           created="",
                           hostname="",
                           name="",
                           project="12e1b1db-44d7-4f57-9c9d-5799b582ab8f",
                           reinstall=False,
                           ssh_pub_keys=[],
                           succeeded=True,
                           networks=[
                               models.V1MachineNetwork(
                                   asn="",
                                   destinationprefixes=[],
                                   ips=[],
                                   nat=True,
                                   underlay=False,
                                   private=False,
                                   networkid="",
                                   networktype="external",
                                   prefixes=[],
                                   vrf=0,
                               ),
                           ],
                       ),
                   )
               ]
           ])
    def test_firewall_present_already_exists(self, mocks):
        set_module_args(
            dict(
                api_url="http://somewhere",
                api_hmac="hmac",
                name="test",
                project="12e1b1db-44d7-4f57-9c9d-5799b582ab8f"
            )
        )

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        mocks.assert_called()
        mocks.assert_called_with(models.V1FirewallFindRequest(
            allocation_project="12e1b1db-44d7-4f57-9c9d-5799b582ab8f",
            allocation_name="test",
        ))

        expected = dict(
            id="5345b85e-9841-4699-b20e-0efaa806b690",
            changed=False,
        )
        self.assertDictEqual(result.exception.module_results, expected)

    @patch("metal_python.api.firewall_api.FirewallApi.find_firewalls",
           side_effect=[[]])
    @patch("metal_python.api.firewall_api.FirewallApi.allocate_firewall",
           side_effect=[
               models.V1FirewallResponse(
                   id="5345b85e-9841-4699-b20e-0efaa806b690",
                   bios=models.V1MachineBIOS(
                       _date="",
                       vendor="",
                       version="",
                   ),
                   events=[],
                   hardware=models.V1MachineHardware(
                       cpu_cores=4,
                       disks=[],
                       memory=1024,
                       nics=[],
                   ),
                   ledstate="",
                   liveliness="Alive",
                   state="",
                   tags=["ci.metal-stack.io/manager=ansible"],
                   allocation=models.V1MachineAllocation(
                       created="",
                       hostname="",
                       name="",
                       project="12e1b1db-44d7-4f57-9c9d-5799b582ab8f",
                       reinstall=False,
                       ssh_pub_keys=[],
                       succeeded=True,
                       networks=[
                           models.V1MachineNetwork(
                               asn="",
                               destinationprefixes=[],
                               ips=[],
                               nat=True,
                               underlay=False,
                               private=False,
                               networkid="",
                               networktype="external",
                               prefixes=[],
                               vrf=0,
                           ),
                       ],
                   ),
               )
           ])
    def test_firewall_present_allocate(self, allocate_mock, find_mock):
        set_module_args(
            dict(
                api_url="http://somewhere",
                api_hmac="hmac",
                name="test2",
                project="12e1b1db-44d7-4f57-9c9d-5799b582ab8f",
                partition="partition-id",
                size="c1",
                image="ubuntu",
            )
        )

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        find_mock.assert_called()
        find_mock.assert_called_with(models.V1FirewallFindRequest(
            allocation_project="12e1b1db-44d7-4f57-9c9d-5799b582ab8f",
            allocation_name="test2",
        ))
        allocate_mock.assert_called()
        allocate_mock.assert_called_with(models.V1FirewallCreateRequest(
            name="test2",
            projectid="12e1b1db-44d7-4f57-9c9d-5799b582ab8f",
            imageid="ubuntu",
            partitionid="partition-id",
            sizeid="c1",
            networks=[],
            ips=[],
            ssh_pub_keys=[],
            tags=["ci.metal-stack.io/manager=ansible"],
        ))

        expected = dict(
            id="5345b85e-9841-4699-b20e-0efaa806b690",
            changed=True,
        )
        self.assertDictEqual(result.exception.module_results, expected)

    @patch("metal_python.api.firewall_api.FirewallApi.find_firewalls",
           side_effect=[
               [
                   models.V1FirewallResponse(
                       id="5345b85e-9841-4699-b20e-0efaa806b690",
                       bios=models.V1MachineBIOS(
                           _date="",
                           vendor="",
                           version="",
                       ),
                       events=[],
                       hardware=models.V1MachineHardware(
                           cpu_cores=4,
                           disks=[],
                           memory=1024,
                           nics=[],
                       ),
                       ledstate="",
                       liveliness="Alive",
                       state="",
                       tags=["ci.metal-stack.io/manager=ansible"],
                       allocation=models.V1MachineAllocation(
                           created="",
                           hostname="",
                           name="",
                           project="12e1b1db-44d7-4f57-9c9d-5799b582ab8f",
                           reinstall=False,
                           ssh_pub_keys=[],
                           succeeded=True,
                           networks=[
                               models.V1MachineNetwork(
                                   asn="",
                                   destinationprefixes=[],
                                   ips=[],
                                   nat=True,
                                   underlay=False,
                                   private=False,
                                   networkid="",
                                   networktype="external",
                                   prefixes=[],
                                   vrf=0,
                               ),
                           ],
                       ),
                   )
               ]
           ])
    @patch("metal_python.api.machine_api.MachineApi.free_machine",
           side_effect=[
               models.V1MachineResponse(
                   id="5345b85e-9841-4699-b20e-0efaa806b690",
                   bios=models.V1MachineBIOS(
                       _date="",
                       vendor="",
                       version="",
                   ),
                   events=[],
                   hardware=models.V1MachineHardware(
                       cpu_cores=4,
                       disks=[],
                       memory=1024,
                       nics=[],
                   ),
                   ledstate="",
                   liveliness="Alive",
                   state="",
                   tags=["ci.metal-stack.io/manager=ansible"],
                   allocation=models.V1MachineAllocation(
                       created="",
                       hostname="",
                       name="",
                       project="12e1b1db-44d7-4f57-9c9d-5799b582ab8f",
                       reinstall=False,
                       ssh_pub_keys=[],
                       succeeded=True,
                       networks=[
                           models.V1MachineNetwork(
                               asn="",
                               destinationprefixes=[],
                               ips=[],
                               nat=True,
                               underlay=False,
                               private=False,
                               networkid="",
                               networktype="external",
                               prefixes=[],
                               vrf=0,
                           ),
                       ],
                   ),
               )
           ])
    def test_machine_absent(self, free_mock, find_mock):
        set_module_args(
            dict(
                api_url="http://somewhere",
                api_hmac="hmac",
                name="test2",
                project="12e1b1db-44d7-4f57-9c9d-5799b582ab8f",
                state="absent"
            )
        )

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        find_mock.assert_called()
        find_mock.assert_called_with(models.V1FirewallFindRequest(
            allocation_project="12e1b1db-44d7-4f57-9c9d-5799b582ab8f",
            allocation_name="test2",
        ))
        free_mock.assert_called()
        free_mock.assert_called_with("5345b85e-9841-4699-b20e-0efaa806b690")

        expected = dict(
            id="5345b85e-9841-4699-b20e-0efaa806b690",
            changed=True,
        )
        self.assertDictEqual(result.exception.module_results, expected)
