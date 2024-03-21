#!/usr/bin/python
# -*- coding: utf-8 -*-
try:
    from metal_python.api import FirewallApi, MachineApi
    from metal_python import models
    from metal_python import rest

    METAL_PYTHON_AVAILABLE = True
except ImportError:
    METAL_PYTHON_AVAILABLE = False

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.metal import AUTH_SPEC, ANSIBLE_CI_MANAGED_TAG, init_driver_for_module

ANSIBLE_METADATA = {
    'metadata_version': '0.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: metal_firewall

short_description: A module to manage metal firewall entities

version_added: "2.8"

description:
    - Manages firewall entities in the metal-api.
    - Requires metal_python to be installed.

options:
    id:
        description:
            - The id of the firewall, user for specific firewall allocation.
        required: false
    name:
        description:
            - >-
              The name of the firewall, which must be unique within a project and partition
              (in case id is not provided).
              Otherwise, the module cannot figure out if the firewall was already created or not.
        required: false
    description:
        description:
            - The description of the firewall.
        required: false
    hostname:
        description:
            - The hostname of the firewall.
        required: false
    project:
        description:
            - The project of the firewall.
        required: true
    partition:
        description:
            - The partition of the firewall.
        required: false
    image:
        description:
            - The image of the firewall.
        required: false
    size:
        description:
            - The size of the firewall.
        required: false
    networks:
        description:
            - The networks of the firewall.
        required: false
    ips:
        description:
            - The ips of the firewall.
        required: false
    rules:
        description:
            - Firewall rules to be deployed to the firewall during provisioning. By default the firewall drops all traffic from the node's private network.
        required: false
    tags:
        description:
            - The tags of the firewall.
        required: false
    state:
        description:
          - Assert the state of the firewall.
          - >-
            Use C(present) to create or update a firewall and C(absent) to
            release it.
        default: present
        choices:
          - absent
          - present

author:
    - metal-stack
'''

EXAMPLES = '''
- name: allocate a firewall
  metal_firewall:
    name: my-firewall
    description: "my firewall"
    hostname: my-firewall
    networks:
    - internet
    - 5d30b3af-cb2a-4aa3-84e8-52dbf94a326b
    size: c1-xlarge-x86
    partition: fra-equ01
    project: 9ec6882a-cd94-42a7-b667-ffaed43557c7
    rules:
      ingress:
        - comment: ssh
          source:
            - 192.168.2.0/24
          ports: [22]
          protocol: tcp
      egress:
        - comment: reach out to internet
          ports: [53,80,123,443]
          to:
            - 0.0.0.0/0

- name: release a firewall
  metal_firewall:
    id: 306bc4ad-33cd-4744-8c6a-6b601f7179ea
    state: absent
'''

RETURN = '''
id:
  description:
    - firewall id
  returned: always
  type: str
  sample: 306bc4ad-33cd-4744-8c6a-6b601f7179ea
'''


class Instance(object):
    def __init__(self, module):
        if not METAL_PYTHON_AVAILABLE:
            raise RuntimeError("metal_python must be installed")

        self._module = module
        self.changed = False
        self._firewall = None
        self.id = module.params.get('id')
        self._name = module.params.get('name')
        self._description = module.params.get('description')
        self._hostname = module.params.get('hostname')
        self._project = module.params.get('project')
        self._partition = module.params.get('partition')
        self._image = module.params.get('image')
        self._size = module.params.get('size')
        self._networks = module.params.get('networks') if module.params.get('networks') else []
        self._ips = module.params.get('ips') if module.params.get('ips') else []
        self._tags = module.params.get('tags') if module.params.get('tags') else []
        self._ssh_pub_keys = module.params.get('ssh_pub_keys')
        self._userdata = module.params.get('userdata')
        self._rules = module.params.get('rules')
        self._state = module.params.get('state')
        self._driver = init_driver_for_module(self._module)
        self._api_client = FirewallApi(api_client=self._driver.client)
        self._machine_api_client = MachineApi(api_client=self._driver.client)

        if self.id is None and (self._project is None or self._name is None):
            module.fail_json(msg="either id or name must be given")

    def run(self):
        if self._module.check_mode:
            return

        self._find()

        if self._state == "present":
            if self._firewall:
                return

            self._allocate()
            self.changed = True

        elif self._state == "absent":
            if not self.id:
                self._module.fail_json(msg="id is a required argument when state is absent")
            if self._firewall:
                self._free()
                self.changed = True

    def _find(self):
        if self.id:
            self._firewall = self._api_client.find_firewall(self.id)
            return

        r = models.V1FirewallFindRequest(
            allocation_name=self._name,
            allocation_project=self._project,
        )
        try:
            firewalls = self._api_client.find_firewalls(r)
        except rest.ApiException as e:
            self._module.fail_json(msg="request to metal-api failed", error=str(e))
            return

        if len(firewalls) > 1:
            self._module.fail_json(
                msg="multiple firewalls of name '%s' exist in project '%s'. "
                    "module idempotence depends on unique names within a project, "
                    "please ensure unique names or id in params.",
                project=self._project, name=self._name)
        elif len(firewalls) == 1:
            self._firewall = firewalls[0]
            self.id = self._firewall.id

    def _allocate(self):
        networks = list()
        for n in self._networks:
            networks.append(models.V1MachineAllocationNetwork(autoacquire=True, networkid=n))

        self._tags.append(ANSIBLE_CI_MANAGED_TAG)

        r = models.V1FirewallCreateRequest(
            uuid=self.id if self.id else None,
            name=self._name,
            description=self._description,
            hostname=self._hostname,
            partitionid=self._partition,
            projectid=self._project,
            imageid=self._image,
            ips=self._ips,
            sizeid=self._size,
            networks=networks,
            tags=self._tags,
            ssh_pub_keys=self._ssh_pub_keys,
            user_data=self._userdata,
        )

        if self._rules:
            rules = models.V1FirewallRules(
                ingress=[],
                egress=[],
            )

            for rule in self._rules.get('ingress', []):
                elem = models.V1FirewallIngressRule(
                    _from=rule.get('source'),
                    ports=rule.get('ports'),
                    to=rule.get('to', []),
                )

                if rule.get('comment'):
                    elem.comment = rule.get('comment')
                if rule.get('protocol'):
                    elem.protocol = rule.get('protocol')

                rules.ingress.append(elem)

            for rule in self._rules.get('egress', []):
                elem = models.V1FirewallEgressRule(
                    ports=rule.get('ports'),
                    protocol=rule.get('protocol'),
                    to=rule.get('to'),
                )

                if rule.get('comment'):
                    elem.comment = rule.get('comment')
                if rule.get('protocol'):
                    elem.protocol = rule.get('protocol')

                rules.egress.append(elem)

            r.firewall_rules = rules

        try:
            self._firewall = self._api_client.allocate_firewall(r)
        except rest.ApiException as e:
            self._module.fail_json(msg="request to metal-api failed", error=str(e))

        self.id = self._firewall.id

    def _free(self):
        if ANSIBLE_CI_MANAGED_TAG not in self._firewall.tags:
            self._module.fail_json(msg="entity does not have label attached: %s" % ANSIBLE_CI_MANAGED_TAG,
                                   project=self._project,
                                   name=self._name)

        try:
            self._machine_api_client.free_machine(self.id)
        except rest.ApiException as e:
            self._module.fail_json(msg="request to metal-api failed", error=str(e))


def main():
    argument_spec = AUTH_SPEC.copy()
    argument_spec.update(dict(
        id=dict(type='str', required=False),
        name=dict(type='str', required=False),
        description=dict(type='str', required=False),
        hostname=dict(type='str', required=False),
        project=dict(type='str', required=True),
        partition=dict(type='str', required=False),
        image=dict(type='str', required=False),
        size=dict(type='str', required=False),
        networks=dict(type='list', required=False),
        ips=dict(type='list', required=False),
        tags=dict(type='list', default=list(), required=False),
        ssh_pub_keys=dict(type='list', default=list(), required=False),
        userdata=dict(type='str', required=False),
        rules=dict(type='dict', required=False, options=dict(
            ingress=dict(type='list', required=False, options=dict(
                comment=dict(type='str', required=False),
                source=dict(type='list', required=True),
                ports=dict(type='list', required=True),
                protocol=dict(type='str', required=False),
                to=dict(type='list', required=False),
            )),
            egress=dict(type='list', required=False, options=dict(
                comment=dict(type='str', required=False),
                ports=dict(type='list', required=True),
                protocol=dict(type='str', required=False),
                to=dict(type='list', required=True),
            )),
        )),
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
    )

    module.exit_json(**result)


if __name__ == '__main__':
    main()
