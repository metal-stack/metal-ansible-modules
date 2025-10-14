#!/usr/bin/python
# -*- coding: utf-8 -*-

from datetime import datetime
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.metal_v2 import V2_AUTH_SPEC, init_client_for_module, parse_delta


try:
    from connectrpc.errors import ConnectError
    from google.protobuf.json_format import MessageToDict

    from metalstack.api.v2 import common_pb2, token_pb2
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
module: metal_v2_api_token

short_description: A module to manage api token entities.

version_added: "2.18"

description:
    - Manages api token entities in the metal-apiserver.
    - Requires metal-stack-api to be installed.

options:
    description:
        description:
            - The description of the token, which must be unique for the user who creates the api token.
              Otherwise, the module cannot figure out if the token was already created or not.
        required: true
    admin_role:
        description:
            - The admin role for this token.
        required: false
    tenant_roles:
        description:
            - A map of tenant identifiers to tenant roles.
        required: false
    project_roles:
        description:
            - A map of project identifiers to tenant roles.
        required: false
    permissions:
        description:
            - A list of api-method permissions.
        required: false
    expires:
        description:
            - The duration until this token expires. This field cannot be updated and is only used on token creation.
        required: false
    state:
        description:
          - Assert the state of the token.
          - >-
            Use C(present) to create or update a token and C(absent) to
            delete it.
        default: present
        choices:
          - absent
          - present

author:
    - metal-stack
'''

EXAMPLES = '''
- name: create a token
  metal_v2_token:
    description: an infra component token
    permissions:
    - subject: 3e977e81-6ab5-4f28-b608-e7e94d62efb7
      methods:
        - /metalstack.infra.v2.BMCService/UpdateBMCInfo

- name: revoke a token
  metal_v2_token:
    description: an infra component token
    state: absent
'''

RETURN = '''
id:
    description:
        - token id
    returned: ifexisted but not returned on deletion
    type: str
    sample: ae6834bd-1ca8-4d22-b38a-8a7c771c06b0
token:
    description: for metal-bmc
    expires: '2025-01-01T14:00:00.00000000Z'
    issuedAt: '2025-01-01T12:00:00.00000000Z'
    permissions:
    -   methods:
        - /metalstack.infra.v2.BMCService/UpdateBMCInfo
        subject: e0588ffb-8e95-4f51-ba68-721cbf798543
    tokenType: TOKEN_TYPE_API
    user: user@oidc
    uuid: ae6834bd-1ca8-4d22-b38a-8a7c771c06b0
'''


class Instance(object):
    def __init__(self, module):
        if not METAL_STACK_API_AVAILABLE:
            raise RuntimeError("metal-stack-api must be installed")

        self._module = module
        self.changed = False
        self._token: token_pb2.Token = None
        self._uuid = None
        self._description = module.params.get('description')
        self._expires = parse_delta(module.params.get(
            'expires')) if module.params.get('expires') else None
        self._project_roles = module.params.get('project_roles')
        self._tenant_roles = module.params.get('tenant_roles')
        self._admin_role = module.params.get('admin_role')
        self._permissions = module.params.get('permissions')
        self._state = module.params.get('state')
        self._client: apiclient.Client = init_client_for_module(module)

    def run(self):
        if self._module.check_mode:
            return

        self._find()

        if self._state == "present":
            if self._token:
                self._update()
                return

            self._create()
            self.changed = True

        elif self._state == "absent":
            if self._token:
                self._delete()
                self.changed = True

    def _find(self):
        # TODO: some search filters would be useful in the API?
        r = token_pb2.TokenServiceListRequest()

        try:
            resp = self._client.apiv2().token().list(request=r)
        except ConnectError as e:
            self._module.fail_json(
                msg="request to metal-apiserver failed", error=str(e))
            return

        tokens = []

        for token in resp.tokens:
            if token.token_type != token_pb2.TOKEN_TYPE_API:
                continue

            if token.description == self._description:
                tokens.append(token)

        if not tokens:
            return

        if len(tokens) > 1:
            self._module.fail_json(
                msg="token description is not unique within the user, which is required when "
                    "using this module", name=self._name)
        elif len(tokens) == 1:
            self._token = tokens[0]
            self._uuid = self._token.uuid

    def _update(self):
        r = token_pb2.TokenServiceUpdateRequest(
            uuid=self._uuid,
            update_meta=common_pb2.UpdateMeta(
                locking_strategy=common_pb2.OPTIMISTIC_LOCKING_STRATEGY_CLIENT,
                updated_at=datetime.now(),
            ),
            # if we do not send permissions, they will be gone in case they do not change (bug?):
            permissions=self._token.permissions,
        )

        # TODO: tokens currently have no labels
        # if not self._token.meta.labels.labels.get(V2_ANSIBLE_CI_MANAGED_KEY, "") == V2_ANSIBLE_CI_MANAGED_VALUE:
        #     self._module.fail_json(
        #         msg=f"refusing to update because label is not present on entity: {V2_ANSIBLE_CI_MANAGED_KEY}={V2_ANSIBLE_CI_MANAGED_VALUE}")
        #     return

        if self._permissions:
            new_permissions = []

            for permission in self._permissions:
                new_permissions.append(token_pb2.MethodPermission(
                    subject=permission.get("subject"),
                    methods=permission.get("methods", []),
                ))

            if new_permissions != self._token.permissions:
                self.changed = True
                r.permissions.extend(new_permissions)

        if self._admin_role and common_pb2.AdminRole.Value(self._admin_role) != self._token.admin_role:
            self.changed = True
            r.admin_role = self._admin_role

        if self._project_roles:
            new_roles = {}

            for role in self._project_roles:
                new_roles[role.get("id")] = common_pb2.ProjectRole.Value(
                    role.get("role"))

            if new_roles != self._token.project_roles:
                self.changed = True
                r.project_roles.update(new_roles)

        if self._tenant_roles:
            new_roles = {}

            for role in self._tenant_roles:
                new_roles[role.get("id")] = common_pb2.TenantRole.Value(
                    role.get("role"))

            if new_roles != self._token.tenant_roles:
                self.changed = True
                r.tenant_roles.update(new_roles)

        # if self._labels:
        #     # self._labels[V2_ANSIBLE_CI_MANAGED_KEY] = V2_ANSIBLE_CI_MANAGED_VALUE

        #     if self._token.meta.labels != self._labels:
        #         self.changed = True
        #         r.labels = self._labels

        if self.changed:
            try:
                resp = self._client.apiv2().token().update(r)
                self._token = resp.token
            except ConnectError as e:
                self._module.fail_json(
                    msg="request to metal-apiserver failed", error=str(e))

    def _create(self):
        # TODO: tokens currently have no labels
        # labels = {
        #     V2_ANSIBLE_CI_MANAGED_KEY: V2_ANSIBLE_CI_MANAGED_VALUE,
        # }

        r = token_pb2.TokenServiceCreateRequest(
            description=self._description,
        )

        if self._expires:
            r.expires = self._expires

        for permission in self._permissions:
            r.permissions.append(token_pb2.MethodPermission(
                subject=permission.get("subject"),
                methods=permission.get("methods", []),
            ))

        if self._admin_role and common_pb2.AdminRole.Value(self._admin_role):
            r.admin_role = self._admin_role

        if self._project_roles:
            for role in self._project_roles:
                r.project_roles[role.get("id")] = common_pb2.ProjectRole.Value(
                    role.get("role"))

        if self._tenant_roles:
            for role in self._tenant_roles:
                r.tenant_roles[role.get("id")] = common_pb2.TenantRole.Value(
                    role.get("role"))

        try:
            resp = self._client.apiv2().token().create(r)
            self._token = resp.token
        except ConnectError as e:
            self._module.fail_json(
                msg="request to metal-apiserver failed", error=str(e))

        self._uuid = self._token.uuid

    def _delete(self):
        # TODO: tokens currently have no labels
        # if not self._token.meta.labels.labels.get(V2_ANSIBLE_CI_MANAGED_KEY, "") == V2_ANSIBLE_CI_MANAGED_VALUE:
        #     self._module.fail_json(
        #         msg=f"refusing to delete because label is not present on entity: {V2_ANSIBLE_CI_MANAGED_KEY}={V2_ANSIBLE_CI_MANAGED_VALUE}")
        #     return

        try:
            self._client.apiv2().token().revoke(token_pb2.TokenServiceRevokeRequest(
                uuid=self._uuid,
            ))
        except ConnectError as e:
            self._module.fail_json(
                msg="request to metal-apiserver failed", error=str(e))


def main():
    argument_spec = V2_AUTH_SPEC.copy()
    argument_spec.update(dict(
        description=dict(type='str', required=True),
        expires=dict(type='str', required=False),
        permissions=dict(type='list', required=False, elements='dict', options=dict(
            subject=dict(type='str', required=True),
            methods=dict(type='list', elements='str'),
        )),
        project_roles=dict(type='list', required=False, elements='dict', options=dict(
            id=dict(type='str', required=True),
            role=dict(type='str', required=True),
        )),
        tenant_roles=dict(type='list', required=False, elements='dict', options=dict(
            id=dict(type='str', required=True),
            role=dict(type='str', required=True),
        )),
        admin_role=dict(type='str', required=False),
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
        id=instance._uuid,
    )

    if instance._token:
        result['token'] = MessageToDict(instance._token)

    module.exit_json(**result)


if __name__ == '__main__':
    main()
