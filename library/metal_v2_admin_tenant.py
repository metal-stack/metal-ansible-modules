#!/usr/bin/python
# -*- coding: utf-8 -*-

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.metal_v2 import BaseMetalV2Resource


try:
    from connectrpc.errors import ConnectError
    from google.protobuf.json_format import MessageToDict

    from metalstack.api.v2 import common_pb2, tenant_pb2
    from metalstack.admin.v2 import tenant_pb2 as admin_tenant_pb2
except ImportError:
    pass


ANSIBLE_METADATA = {
    'metadata_version': '1.0',
    'status': ['stableinterface'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: metal_v2_admin_tenant

short_description: A module to manage metal tenant entities.

version_added: "2.18"

description:
    - Manages tenant entities in the metal-apiserver.
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

requirements:
    - L(metal-stack-api,https://pypi.org/project/metal-stack-api/)
'''

EXAMPLES = '''
- name: create a tenant
  metal_v2_admin_tenant:
    identifier: my-tenant
    name: my-tenant
    description: test tenant
    avatar_url: http://test
    email: test@test.com

- name: delete a tenant
  metal_v2_admin_tenant:
    identifier: my-tenant
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
    description:
        - tenant response
    returned: ifexisted
    type: dict
    sample:
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
        r = admin_tenant_pb2.TenantServiceListRequest(
            query=tenant_pb2.TenantQuery(
                labels=common_pb2.Labels(
                    labels={
                        self.V2_ANSIBLE_CI_IDENTIFIER_KEY: self._identifier,
                        self.V2_ANSIBLE_CI_MANAGED_KEY: self.V2_ANSIBLE_CI_MANAGED_VALUE,
                    },
                ),
            ),
        )

        try:
            resp = self._client.adminv2().tenant().list(request=r, headers=self._headers)
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
            labels = self._build_labels()

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
        labels = self._build_labels()

        r = admin_tenant_pb2.TenantServiceCreateRequest(
            name=self._name,
            description=self._description,
            labels=common_pb2.Labels(labels=labels),
        )

        if self._avatar_url:
            r.avatar_url = self._avatar_url
        if self._email:
            r.email = self._email

        try:
            resp = self._client.adminv2().tenant().create(request=r, headers=self._headers)
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
    module = AnsibleModule(
        argument_spec=BaseMetalV2Resource._create_argument_spec(dict(
            name=dict(type='str', required=True),
            description=dict(type='str', required=True),
            avatar_url=dict(type='str', required=False),
            email=dict(type='str', required=False),
        )),
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
