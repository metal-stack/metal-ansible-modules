#!/usr/bin/python
# -*- coding: utf-8 -*-

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.metal_v2 import BaseMetalV2Resource


try:
    from connectrpc.errors import ConnectError
    from google.protobuf.json_format import MessageToDict

    from metalstack.api.v2 import common_pb2, ip_pb2

    IP_TYPES = {
        'ephemeral': ip_pb2.IP_TYPE_EPHEMERAL,
        'static': ip_pb2.IP_TYPE_STATIC,
    }

    IP_ADDRESS_FAMILIES = {
        'ipv4': ip_pb2.IP_ADDRESS_FAMILY_V4,
        'ipv6': ip_pb2.IP_ADDRESS_FAMILY_V6,
    }
except ImportError:
    pass


ANSIBLE_METADATA = {
    'metadata_version': '0.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: metal_v2_ip

short_description: A module to manage metal ip entities.

version_added: "2.18"

description:
    - Manages ip entities in the metal-apiserver.
    - Requires metal-stack-api to be installed.
    - Authentication can be provided via the I(api_url) and I(api_token) options or the METAL_APIV2_URL and METAL_APIV2_TOKEN environment variables.
    - An optional I(api_timeout) can be set to limit the request duration.

options:
    identifier:
        description:
            - A resource identifier for resources that have auto-generated uuids.
              The identifier gets stored in the resource labels.
              With this, the module can figure out if the resource already exists using the identifier label.
              If multiple resources with the same identifier label are found, the module will throw an error.
        required: true
    use_latest_identifier:
        description:
            - If set to true and multiple resources with the same identifier label are found, the module acts on the latest created resource.
            - If set to false (default) and multiple resources match, the module will fail with an error.
        required: false
        default: false
    project:
        description:
            - The project of the ip.
            - This field cannot be changed after the ip was allocated.
        required: true
    network:
        description:
            - The network to allocate the ip from.
            - Required when I(state=present).
            - This field cannot be changed after the ip was allocated.
        required: false
    ip:
        description:
            - A specific ip address to allocate. If not given, a random ip address is allocated from the network.
            - This field cannot be changed after the ip was allocated.
        required: false
    name:
        description:
            - The name of the ip.
        required: false
    description:
        description:
            - The description of the ip.
        required: false
    type:
        description:
            - The type of the ip.
        required: false
        default: ephemeral
        choices:
          - ephemeral
          - static
    address_family:
        description:
            - The address family of the ip to allocate, only used on creation.
            - Only needs to be provided when the network contains prefixes of both address families.
        required: false
        choices:
          - ipv4
          - ipv6
    machine:
        description:
            - The uuid of the machine to associate the ip with, only used on creation.
        required: false
    labels:
        description:
            - The labels of the ip.
            - Set to empty dict in order to clean existing.
        required: false
    state:
        description:
          - Assert the state of the ip.
          - >-
            Use C(present) to allocate or update an ip and C(absent) to
            free it.
        default: present
        choices:
          - absent
          - present

author:
    - metal-stack
'''

EXAMPLES = '''
- name: allocate a random static ip
  metal_v2_ip:
    identifier: my-ip
    name: my-ip
    description: my static ip
    project: 3e977e81-6ab5-4f28-b608-e7e94d62efb7
    network: internet
    type: static

- name: allocate a specific ip
  metal_v2_ip:
    identifier: my-specific-ip
    ip: 203.0.113.10
    project: 3e977e81-6ab5-4f28-b608-e7e94d62efb7
    network: internet
    type: static

- name: free an ip
  metal_v2_ip:
    identifier: my-ip
    project: 3e977e81-6ab5-4f28-b608-e7e94d62efb7
    state: absent
'''

RETURN = '''
id:
    description:
        - ip uuid
    returned: ifexisted
    type: str
    sample: 9f9e6a0c-1a4e-4a8b-a3c2-5d3c7e0f4b11
address:
    description:
        - ip address
    returned: ifexisted
    type: str
    sample: 203.0.113.10
ip:
    description:
        - ip response
    returned: ifexisted
    type: dict
    sample:
        description: my static ip
        ip: 203.0.113.10
        meta:
            createdAt: '2025-01-01T12:00:00.00000000Z'
            labels:
                labels:
                    ci.metal-stack.io/id: my-ip
                    ci.metal-stack.io/manager: ansible
        name: my-ip
        network: internet
        project: 3e977e81-6ab5-4f28-b608-e7e94d62efb7
        type: IP_TYPE_STATIC
        uuid: 9f9e6a0c-1a4e-4a8b-a3c2-5d3c7e0f4b11
'''


class Instance(BaseMetalV2Resource):
    def __init__(self, module):
        super().__init__(module)
        self._ip: ip_pb2.IP = None
        self._uuid = None
        self._address = None
        self._project = module.params['project']
        self._network = module.params.get('network')
        self._requested_address = module.params.get('ip')
        self._name = module.params.get('name')
        self._description = module.params.get('description')
        self._type = IP_TYPES[module.params['type']]
        self._address_family = module.params.get('address_family')
        self._machine = module.params.get('machine')

    def _get_resource(self):
        return self._ip

    def _set_ip(self, ip):
        self._ip = ip
        if ip:
            self._uuid = ip.uuid
            self._address = ip.ip

    def _find(self):
        r = ip_pb2.IPServiceListRequest(
            project=self._project,
            query=ip_pb2.IPQuery(
                labels=common_pb2.Labels(
                    labels={
                        self.V2_ANSIBLE_CI_IDENTIFIER_KEY: self._identifier,
                        self.V2_ANSIBLE_CI_MANAGED_KEY: self.V2_ANSIBLE_CI_MANAGED_VALUE,
                    },
                ),
            ),
        )

        try:
            resp = self._client.apiv2().ip().list(request=r, headers=self._headers)
        except ConnectError as e:
            self._module.fail_json(
                msg="request to metal-apiserver failed", error=str(e))
            return

        self._set_ip(self._get_latest_resource(resp.ips))

    def _update(self):
        if self._requested_address and self._ip.ip != self._requested_address:
            self._module.fail_json(
                msg=f"ip has address {self._ip.ip}, it cannot be changed to {self._requested_address}")
            return

        if self._network and self._ip.network != self._network:
            self._module.fail_json(
                msg=f"ip belongs to network {self._ip.network}, it cannot be changed to network {self._network}")
            return

        r = ip_pb2.IPServiceUpdateRequest(
            ip=self._address,
            project=self._project,
            update_meta=common_pb2.UpdateMeta(
                locking_strategy=common_pb2.OPTIMISTIC_LOCKING_STRATEGY_CLIENT,
                updated_at=self._ip.meta.updated_at,
            ),
        )

        if self._name is not None and self._ip.name != self._name:
            self.changed = True
            r.name = self._name

        if self._description is not None and self._ip.description != self._description:
            self.changed = True
            r.description = self._description

        if self._ip.type != self._type:
            self.changed = True
            r.type = self._type

        if self._labels is not None:
            labels = self._build_labels()

            if self._ip.meta.labels.labels != labels:
                self.changed = True
                r.labels.CopyFrom(common_pb2.UpdateLabels(
                    replace=common_pb2.Labels(labels=labels)
                ))

        if self.changed:
            try:
                resp = self._client.apiv2().ip().update(request=r, headers=self._headers)
                self._set_ip(resp.ip)
            except ConnectError as e:
                self._module.fail_json(
                    msg="request to metal-apiserver failed", error=str(e))

    def _create(self):
        labels = self._build_labels()

        r = ip_pb2.IPServiceCreateRequest(
            project=self._project,
            network=self._network,
            type=self._type,
            labels=common_pb2.Labels(labels=labels),
        )

        if self._name:
            r.name = self._name
        if self._description:
            r.description = self._description
        if self._requested_address:
            r.ip = self._requested_address
        if self._machine:
            r.machine = self._machine
        if self._address_family:
            r.address_family = IP_ADDRESS_FAMILIES[self._address_family]

        try:
            resp = self._client.apiv2().ip().create(request=r, headers=self._headers)
            self._set_ip(resp.ip)
        except ConnectError as e:
            self._module.fail_json(
                msg="request to metal-apiserver failed", error=str(e))

    def _delete(self):
        try:
            resp = self._client.apiv2().ip().delete(ip_pb2.IPServiceDeleteRequest(
                ip=self._address,
                project=self._project,
            ), headers=self._headers)
            self._set_ip(resp.ip)
        except ConnectError as e:
            self._module.fail_json(
                msg="request to metal-apiserver failed", error=str(e))


def main():
    module = AnsibleModule(
        argument_spec=BaseMetalV2Resource._create_argument_spec(dict(
            project=dict(type='str', required=True),
            network=dict(type='str', required=False),
            ip=dict(type='str', required=False),
            name=dict(type='str', required=False),
            description=dict(type='str', required=False),
            type=dict(type='str', choices=[
                      'ephemeral', 'static'], default='ephemeral'),
            address_family=dict(type='str', choices=[
                                'ipv4', 'ipv6'], required=False),
            machine=dict(type='str', required=False),
        )),
        required_if=[
            ('state', 'present', ['network']),
        ],
        supports_check_mode=True,
    )

    instance = Instance(module)

    instance.run()

    result = dict(
        changed=instance.changed,
        id=instance._uuid,
        address=instance._address,
    )
    if instance._ip:
        result['ip'] = MessageToDict(instance._ip)

    module.exit_json(**result)


if __name__ == '__main__':
    main()
