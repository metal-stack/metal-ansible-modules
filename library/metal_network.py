#!/usr/bin/python
# -*- coding: utf-8 -*-

try:
    from metal_python.api import NetworkApi
    from metal_python import models

    METAL_PYTHON_AVAILABLE = True
except ImportError:
    METAL_PYTHON_AVAILABLE = False

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.metal import AUTH_SPEC, init_driver_for_module

ANSIBLE_METADATA = {
    'metadata_version': '0.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: metal_network

short_description: A module to manage metal network entities

version_added: "2.8"

description:
    - Manages network entities in the metal-api.
    - Requires metal_python to be installed.
    - Cannot update entities.

options:
    name:
        description:
            - >-
              The name of the network, which must be unique within a project and partition.
              Otherwise, the module cannot figure out if the network was already created or not.
        required: true
    description:
        description:
            - The description of the network.
        required: false
    partition:
        description:
            - The partition to allocate the network in.
        required: true
    project:
        description:
            - The project of the network.
        required: true
    state:
        description:
          - Assert the state of the network.
          - >-
            Use C(present) to create or update a network and C(absent) to
            delete it.
        default: present
        choices:
          - absent
          - present

author:
    - metal-stack
'''

EXAMPLES = '''
- name: allocate a network
  metal_network:
    name: my-network
    description: "my network"
    partition: fra-equ01
    project: 9ec6882a-cd94-42a7-b667-ffaed43557c7

- name: free a network
  metal_network:
    name: my-network
    project: 6df6a987-922d-4c36-8cd9-5edbd1584f7a
    partition: fra-equ01
    state: absent
'''

RETURN = '''
id:
    description:
        - network id
    returned: always
    type: str
    sample: 3e977e81-6ab5-4f28-b608-e7e94d62efb7
prefixes:
    description:
        - array of network prefixes
    returned: always
    type: list
    sample: ["10.0.112.0/22"]

'''


class Instance(object):
    def __init__(self, module):
        self._module = module
        self.changed = False
        self.prefixes = None
        self._network = dict()
        self.id = None
        self._id = module.params['id']
        self._name = module.params['name']
        self._project = module.params['project']
        self._partition = module.params['partition']
        self._description = module.params.get('description')
        self._state = module.params.get('state')
        self._driver = init_driver_for_module(self._module)
        self._network_client = NetworkApi(api_client=self._driver.client)

        if self._id is None and (self._partition is None or self._project is None or self._name is None):
            module.fail_json(msg="either id or partition, project and name must be given")

    def run(self):
        if self._module.check_mode:
            return

        self._find()

        if self._state == "present":
            if self._network:
                return

            self._network_allocate()
            self.changed = True

        elif self._state == "absent":
            if self._network:
                self._network_free()
                self.changed = True

    def _find(self):
        if self._id is not None:
            self._network = self._network_client.find_network(self._id)
            self.id = self._network.id
            self.prefixes = self._network.prefixes
            return

        r = models.V1NetworkFindRequest(name=self._name, partitionid=self._partition, projectid=self._project)
        networks = self._network_client.find_networks(r)

        if len(networks) > 1:
            self._module.fail_json(
                msg="network name is not unique within a project and partition, which is required when "
                    "using this module",
                project=self._project, name=self._name)
        elif len(networks) == 1:
            self._network = networks[0]
            self.id = self._network.id
            self.prefixes = self._network.prefixes

    def _network_allocate(self):
        r = models.V1NetworkAllocateRequest(description=self._description, name= self._name, partitionid= self._partition, projectid=self._project)
        self._network = self._network_client.allocate_network(r)
        self.id = self._network.id
        self.prefixes = self._network.prefixes

    def _network_free(self):
        self._network = self._network_client.free_network(self.id)
        self.id = self._network.id
        self.prefixes = self._network.prefixes


def main():
    argument_spec = AUTH_SPEC.copy()
    argument_spec.update(dict(
        id=dict(type='str', required=False),
        name=dict(type='str', required=False),
        project=dict(type='str', required=False),
        description=dict(type='str', required=False),
        partition=dict(type='str', required=False),
        state=dict(type='str', choices=['present', 'absent'], default='present'),
    ))
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    instance = Instance(module)

    instance.run()

    result = dict(
        changed=instance.changed,
        id=instance.id,
        prefixes=instance.prefixes,
    )

    module.exit_json(**result)


if __name__ == '__main__':
    main()
