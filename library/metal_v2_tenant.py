#!/usr/bin/python
# -*- coding: utf-8 -*-

from datetime import datetime
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.metal_v2 import V2_AUTH_SPEC, V2_ANSIBLE_CI_MANAGED_KEY, V2_ANSIBLE_CI_MANAGED_VALUE, V2_ANSIBLE_CI_IDENTIFIER_KEY, init_client_for_module


try:
    from connectrpc.errors import ConnectError
    from google.protobuf.json_format import MessageToDict

    from metalstack.api.v2 import common_pb2, tenant_pb2
    from metalstack.client import client as apiclient

    METAL_STACK_API_AVAILABLE = True
except ImportError:
    METAL_STACK_API_AVAILABLE = False


ANSIBLE_METADATA = {
    'metadata_version': '0.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: metal_v2_tenant

short_description: A module to manage metal tenant entities.

version_added: "2.18"

description:
    - Manages tenant entities in the metal-apiserver.
    - Requires metal-stack-api to be installed.

options:
    identifier:
        description:
            - A resource identifier for the created resource which must be unique within the managed resource scope for resources that have auto-generated uuids.
              Otherwise, the module cannot figure out if the token was already created or not.
              The identifier gets stored in the resource labels.
        required: true
    name:
        description:
            - The name of the tenant.
        required: true
    description:
        description:
            - The description of the tenant.
        required: true
    avatar_url:
        description:
            - The avatar url of the tenant.
        required: false
    email:
        description:
            - The email of the tenant.
        required: false
    labels:
        description:
            - The labels of the tenant.
        required: false
    state:
        description:
          - Assert the state of the tenant.
          - >-
            Use C(present) to create or update a tenant and C(absent) to
            delete it.
        default: present
        choices:
          - absent
          - present

author:
    - metal-stack
'''

EXAMPLES = '''
- name: create a tenant
  metal_v2_tenant:
    identifier: test
    name: test
    description: test tenant
    avatar_url: http://test
    email: test@test.com

- name: delete a tenant
  metal_v2_tenant:
    identifier: test
    state: absent
'''

RETURN = '''
id:
    description:
        - tenant id
    returned: ifexisted
    type: str
    sample: b5bc5d9f-3ade-4eac-bb8c-eb309045151f
tenant:
    avatarUrl: http://test
    createdBy: user@oidc
    description: test tenant
    email: admin@metal-stack.io
    login: b5bc5d9f-3ade-4eac-bb8c-eb309045151f
    meta:
        createdAt: '2025-01-01T12:00:00.00000000Z'
        labels:
            labels:
                ci.metal-stack.io/id: test
                ci.metal-stack.io/manager: ansible
    name: test
'''


class Instance(object):
    def __init__(self, module):
        if not METAL_STACK_API_AVAILABLE:
            raise RuntimeError("metal-stack-api must be installed")

        self._module = module
        self.changed = False
        self._tenant: tenant_pb2.Tenant = None
        self._login = None
        self._name = module.params['name']
        self._identifier = module.params.get('identifier')
        self._description = module.params.get('description')
        self._avatar_url = module.params.get('avatar_url')
        self._email = module.params.get('email')
        self._labels = module.params.get('labels')
        self._state = module.params.get('state')
        client = init_client_for_module(module)
        self._client: apiclient.Client = client[0]
        self._headers: dict = client[1]

    def run(self):
        if self._module.check_mode:
            return

        self._find()

        if self._state == "present":
            if self._tenant:
                self._update()
                return

            self._create()
            self.changed = True

        elif self._state == "absent":
            if self._tenant:
                self._delete()
                self.changed = True

    def _find(self):
        r = tenant_pb2.TenantServiceListRequest(
            query=tenant_pb2.TenantQuery(
                labels=common_pb2.Labels(
                    labels={
                        V2_ANSIBLE_CI_IDENTIFIER_KEY: self._identifier,
                        V2_ANSIBLE_CI_MANAGED_KEY: V2_ANSIBLE_CI_MANAGED_VALUE,
                    },
                ),
            )
        )

        try:
            resp = self._client.apiv2().tenant().list(request=r, headers=self._headers)
        except ConnectError as e:
            self._module.fail_json(
                msg="request to metal-apiserver failed", error=str(e))
            return

        tenants = resp.tenants

        if tenants is None:
            return

        if len(tenants) > 1:
            self._module.fail_json(
                msg="tenant name is not unique, which is required when "
                    "using this module", name=self._name)
        elif len(tenants) == 1:
            self._tenant = tenants[0]
            self._login = self._tenant.login

    def _update(self):
        r = tenant_pb2.TenantServiceUpdateRequest(
            login=self._login,
            update_meta=common_pb2.UpdateMeta(
                locking_strategy=common_pb2.OPTIMISTIC_LOCKING_STRATEGY_CLIENT,
                updated_at=self._tenant.meta.updated_at,
            ),
        )

        if self._name and self._tenant.name != self._name:
            self.changed = True
            r.name = self._name
        if self._description and self._tenant.description != self._description:
            self.changed = True
            r.description = self._description
        if self._avatar_url and self._tenant.avatar_url != self._avatar_url:
            self.changed = True
            r.avatar_url = self._avatar_url
        if self._email and self._tenant.email != self._email:
            self.changed = True
            r.email = self._email

        if self._labels:
            labels = self._labels | {
                V2_ANSIBLE_CI_IDENTIFIER_KEY: self._identifier,
                V2_ANSIBLE_CI_MANAGED_KEY: V2_ANSIBLE_CI_MANAGED_VALUE,
            }

            if self._tenant.meta.labels != labels:
                self.changed = True
                r.labels.CopyFrom(common_pb2.UpdateLabels(
                    replace=common_pb2.Labels(labels=labels)
                ))

        if self.changed:
            try:
                resp = self._client.apiv2().tenant().update(request=r, headers=self._headers)
                self._tenant = resp.tenant
            except ConnectError as e:
                self._module.fail_json(
                    msg="request to metal-apiserver failed", error=str(e))

    def _create(self):
        labels = self._labels if self._labels else dict()
        labels = labels | {
            V2_ANSIBLE_CI_IDENTIFIER_KEY: self._identifier,
            V2_ANSIBLE_CI_MANAGED_KEY: V2_ANSIBLE_CI_MANAGED_VALUE,
        }

        r = tenant_pb2.TenantServiceCreateRequest(
            name=self._name,
            description=self._description,
            labels=common_pb2.Labels(labels=labels),
        )

        if self._avatar_url:
            r.avatar_url = self._avatar_url
        if self._email:
            r.email = self._email

        try:
            resp = self._client.apiv2().tenant().create(request=r, headers=self._headers)
            self._tenant = resp.tenant
        except ConnectError as e:
            self._module.fail_json(
                msg="request to metal-apiserver failed", error=str(e))

        self._login = self._tenant.login

    def _delete(self):
        try:
            resp = self._client.apiv2().tenant().delete(tenant_pb2.TenantServiceDeleteRequest(
                login=self._login,
            ), headers=self._headers)
            self._tenant = resp.tenant
        except ConnectError as e:
            self._module.fail_json(
                msg="request to metal-apiserver failed", error=str(e))


def main():
    argument_spec = V2_AUTH_SPEC.copy()
    argument_spec.update(dict(
        identifier=dict(type='str', required=True),
        name=dict(type='str', required=True),
        description=dict(type='str', required=True),
        avatar_url=dict(type='str', required=False),
        email=dict(type='str', required=False),
        labels=dict(type='dict', required=False),
        state=dict(type='str', choices=[
                   'present', 'absent'], default='present'),
    ))
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    instance = Instance(module)

    instance.run()

    result = dict(
        changed=instance.changed,
        id=instance._login,
    )

    if instance._tenant:
        result['tenant'] = MessageToDict(instance._tenant)

    module.exit_json(**result)


if __name__ == '__main__':
    main()
