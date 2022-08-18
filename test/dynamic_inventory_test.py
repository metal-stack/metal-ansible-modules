import sys
import unittest

from datetime import datetime
from mock import patch, MagicMock
from test import INVENTORY_PATH
from metal_python import models

sys.path.insert(0, INVENTORY_PATH)
from inventory import metal

test_timestamp = datetime.now()


class TestMetalDynamicInventory(unittest.TestCase):
    def setUp(self):
        self.config_mock = MagicMock()
        self.config_mock.hmac.return_value = "123"
        self.config_mock.url.return_value = "https://metal-api"
        self.config_mock.external_network_id.return_value = "internet"

        self.maxDiff = None

    @patch("metal_python.api.machine_api.MachineApi.find_machines",
           side_effect=[[]])
    @patch("metal_python.api.project_api.ProjectApi.list_projects",
           side_effect=[[]])
    def test_host_list_empty(self, projects_mock, machine_mock):
        inventory = metal.host_list(self.config_mock)

        machine_mock.assert_called()
        machine_mock.assert_called_with(models.V1MachineFindRequest())
        projects_mock.assert_called()
        projects_mock.assert_called_with()

        expected = {'_meta': {'hostvars': {}}}

        self.assertDictEqual(inventory, expected)

    @patch("metal_python.api.machine_api.MachineApi.find_machines",
           side_effect=[[
               models.V1MachineResponse(
                   id="5345b85e-9841-4699-b20e-0efaa806b690",
                   bios=models.V1MachineBIOS(
                       _date="",
                       vendor="",
                       version="",
                   ),
                   events=models.V1MachineRecentProvisioningEvents(
                       crash_loop=False,
                       failed_machine_reclaim=False,
                       incomplete_provisioning_cycles="0",
                       last_event_time=test_timestamp,
                       log=[
                           models.V1MachineProvisioningEvent(
                               event="Installing",
                               message="installing machine...",
                               time=test_timestamp,
                           )
                       ],
                   ),
                   hardware=models.V1MachineHardware(
                       cpu_cores=4,
                       disks=[],
                       memory=1024,
                       nics=[],
                   ),
                   rackid="rack-1",
                   ledstate="",
                   liveliness="Alive",
                   state="",
                   tags=["ci.metal-stack.io/manager=ansible"],
                   size=models.V1SizeResponse(
                       id="c1-xlarge-x86",
                       constraints=[],
                   ),
                   partition=models.V1PartitionResponse(
                       id="partition-a",
                       bootconfig=models.V1PartitionBootConfiguration(),
                   ),
                   allocation=models.V1MachineAllocation(
                       created=test_timestamp,
                       creator="metal-stack",
                       hostname="m-hostname",
                       name="m-name",
                       description="my machine",
                       project="12e1b1db-44d7-4f57-9c9d-5799b582ab8f",
                       reinstall=False,
                       role="machine",
                       ssh_pub_keys=[],
                       succeeded=True,
                       image=models.V1ImageResponse(
                           id="ubuntu",
                           expiration_date=test_timestamp,
                           features=["machine"],
                       ),
                       networks=[
                           models.V1MachineNetwork(
                               asn="",
                               destinationprefixes=[],
                               ips=["10.0.0.1"],
                               nat=False,
                               underlay=False,
                               private=True,
                               networktype="privateprimaryunshared",
                               networkid="bd94cb7f-1531-41ab-9171-fd479425804f",
                               prefixes=[],
                               vrf=5,
                           ),
                           models.V1MachineNetwork(
                               asn="",
                               destinationprefixes=[],
                               ips=["1.2.3.4"],
                               nat=True,
                               underlay=False,
                               private=False,
                               networktype="external",
                               networkid="internet",
                               prefixes=[],
                               vrf=10,
                           ),
                       ],
                   ),
               )
           ]])
    @patch("metal_python.api.project_api.ProjectApi.list_projects",
           side_effect=[[
               models.V1ProjectResponse(
                   description="desc",
                   meta=models.V1Meta(
                       id="12e1b1db-44d7-4f57-9c9d-5799b582ab8f",
                       annotations={
                           "ci.metal-stack.io/manager": "ansible",
                       },
                       labels=[
                           "a-label",
                       ],
                   ),
                   name="project-a",
                   tenant_id="tt",
               )
           ]])
    def test_host_list(self, projects_mock, machine_mock):
        inventory = metal.host_list(self.config_mock)

        machine_mock.assert_called()
        machine_mock.assert_called_with(models.V1MachineFindRequest())
        projects_mock.assert_called()
        projects_mock.assert_called_with()

        expected = {
            '_meta': {
                'hostvars': {
                    'm-hostname': {
                        'ansible_host': '1.2.3.4',
                        'ansible_user': 'metal',
                        'metal_allocated_at': str(test_timestamp),
                        'metal_allocation_succeeded': True,
                        'metal_creator': 'metal-stack',
                        'metal_description': 'my machine',
                        'metal_event_log': [
                            {
                                'event': 'Installing',
                                'message': 'installing machine...',
                                'time': str(test_timestamp),
                            }
                        ],
                        'metal_hostname': 'm-hostname',
                        'metal_id': '5345b85e-9841-4699-b20e-0efaa806b690',
                        'metal_image': 'ubuntu',
                        'metal_image_expiration': str(test_timestamp),
                        'metal_internal_ip': '10.0.0.1',
                        'metal_is_firewall': False,
                        'metal_is_machine': True,
                        'metal_name': 'm-name',
                        'metal_partition': 'partition-a',
                        'metal_project': '12e1b1db-44d7-4f57-9c9d-5799b582ab8f',
                        'metal_rack_id': 'rack-1',
                        'metal_size': 'c1-xlarge-x86',
                        'metal_tags': ['ci.metal-stack.io/manager=ansible'],
                        'metal_tenant': "tt"
                    }
                }
            },
            # host groups
            '12e1b1db-44d7-4f57-9c9d-5799b582ab8f': ['m-hostname'],
            'metal': ['m-hostname'],
            'ubuntu': ['m-hostname'],
            'rack-1': ['m-hostname'],
            'partition-a': ['m-hostname'],
            'c1-xlarge-x86': ['m-hostname'],
        }

        self.assertDictEqual(inventory, expected)
