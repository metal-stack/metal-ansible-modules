#!/usr/bin/python
# -*- coding: utf-8 -*-

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.metal_v2 import BaseMetalV2Resource


try:
    from connectrpc.errors import ConnectError
    from google.protobuf.json_format import MessageToDict

    from metalstack.api.v2 import common_pb2, tenant_pb2

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
            - A resource identifier for resources that have auto-generated uuids.
              The identifier gets stored in the resource labels.
              With this, the module can figure out if the resource already exists using the identifier label.
              If multiple resources with the same identifier label are found, the module will throw an error.
        required: true
    use_latest_identifier:
        description:
            - If set to true and multiple resources with the same identifier label are found, the module acts on the latest created resource.
        required: true
        default: false
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
            - Set to empty dict in order to clean existing.
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


class Instance(BaseMetalV2Resource):
    def __init__(self, module):
        if not METAL_STACK_API_AVAILABLE:
            raise RuntimeError("metal-stack-api must be installed")

        super().__init__(module)
        self._tenant: tenant_pb2.Tenant = None
        self._login = None
        self._name = module.params['name']
        self._description = module.params.get('description')
        self._avatar_url = module.params.get('avatar_url')
        self._email = module.params.get('email')

    def _get_resource(self):
        return self._tenant

    def _find(self):
        r = tenant_pb2.TenantServiceListRequest(
            query=tenant_pb2.TenantQuery(
                labels=common_pb2.Labels(
                    labels={
                        self.V2_ANSIBLE_CI_IDENTIFIER_KEY: self._identifier,
                        self.V2_ANSIBLE_CI_MANAGED_KEY: self.V2_ANSIBLE_CI_MANAGED_VALUE,
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

        self._tenant = self._get_latest_resource(resp.tenants)
        if self._tenant:
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

        if self._labels != None:
            labels = self._labels | {
                self.V2_ANSIBLE_CI_IDENTIFIER_KEY: self._identifier,
                self.V2_ANSIBLE_CI_MANAGED_KEY: self.V2_ANSIBLE_CI_MANAGED_VALUE,
            }

            if self._tenant.meta.labels.labels != labels:
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
            self.V2_ANSIBLE_CI_IDENTIFIER_KEY: self._identifier,
            self.V2_ANSIBLE_CI_MANAGED_KEY: self.V2_ANSIBLE_CI_MANAGED_VALUE,
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

    def _result(self):
        result = dict(
            changed=self.changed,
            id=self._login,
        )
        if self._tenant:
            result['tenant'] = MessageToDict(self._tenant)
        return result


def main():
    module = BaseMetalV2Resource.create_module(dict(
        name=dict(type='str', required=True),
        description=dict(type='str', required=True),
        avatar_url=dict(type='str', required=False),
        email=dict(type='str', required=False),
    ))
    instance = Instance(module)

    instance.run()

    module.exit_json(**instance._result())


if __name__ == '__main__':
    main()
