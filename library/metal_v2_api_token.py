#!/usr/bin/python
# -*- coding: utf-8 -*-

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.metal_v2 import V2_AUTH_SPEC, V2_ANSIBLE_CI_MANAGED_KEY, V2_ANSIBLE_CI_MANAGED_VALUE, V2_ANSIBLE_CI_IDENTIFIER_KEY, init_client_for_module, parse_delta, get_latest_resource


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
    description:
        description:
            - The description of the token.
        required: false
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
    labels:
        - The labels of the token.
        - Set to empty dict in order to clean existing.
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
  metal_v2_api_token:
    identifier: token-list
    description: a token that can list tokens
    permissions:
    - self:
        methods:
            - /metalstack.api.v2.TokenService/List

- name: revoke a token
  metal_v2_api_token:
    identifier: token-list
    state: absent
'''

RETURN = '''
id:
    description:
        - token id
    returned: ifexisted but not returned on deletion
    type: str
    sample: ae6834bd-1ca8-4d22-b38a-8a7c771c06b0
secret:
    description:
        - the token secret
    returned: oncreation
    type: str
    sample: <a-secret-jwt-token>
token:
    description: refresh
    expires: '2026-07-18T11:54:36.591697440Z'
    issuedAt: '2026-07-17T11:54:36.591697440Z'
    meta:
        createdAt: '2026-07-17T11:54:36.591697440Z'
        labels:
            labels:
                ci.metal-stack.io/id: token-refresh
                ci.metal-stack.io/manager: ansible
    permissions:
    -   methods:
        - /metalstack.api.v2.TokenService/Refresh
    tokenType: TOKEN_TYPE_API
    user: metal-stack
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
        self._secret = None
        self._description = module.params.get('description')
        self._identifier = module.params.get('identifier')
        self._use_latest_identifier = module.params.get(
            'use_latest_identifier')
        self._expires = parse_delta(module.params.get(
            'expires')) if module.params.get('expires') else None
        self._project_roles = module.params.get('project_roles')
        self._tenant_roles = module.params.get('tenant_roles')
        self._admin_role = module.params.get('admin_role')
        self._permissions = module.params.get('permissions')
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
        r = token_pb2.TokenServiceListRequest(
            query=token_pb2.TokenQuery(
                labels=common_pb2.Labels(
                    labels={
                        V2_ANSIBLE_CI_IDENTIFIER_KEY: self._identifier,
                        V2_ANSIBLE_CI_MANAGED_KEY: V2_ANSIBLE_CI_MANAGED_VALUE,
                    },
                ),
            ),
        )

        try:
            resp = self._client.apiv2().token().list(request=r, headers=self._headers)
        except ConnectError as e:
            self._module.fail_json(
                msg="request to metal-apiserver failed", error=str(e))
            return

        self._token = get_latest_resource(self, resp.tokens)
        if self._token:
            self._uuid = self._token.uuid

    def _update(self):
        r = token_pb2.TokenServiceUpdateRequest(
            uuid=self._uuid,
            update_meta=common_pb2.UpdateMeta(),
        )

        if self._description and self._token.description != self._description:
            self.changed = True
            r.description = self._description

        if self._permissions:
            old_methods = []
            for perm in self._token.permissions:
                old_methods.extend(perm.methods)
            new_permissions = []
            new_methods = []

            for permission in self._permissions:
                if permission.get("self"):
                    methods = permission.get("self").get("methods", [])
                    new_permissions.append(token_pb2.PermissionsByVisibility(
                        self=token_pb2.SelfPermissions(
                            methods=methods
                        ),
                    ))
                    new_methods.extend(methods)
                if permission.get("infra"):
                    methods = permission.get("infra").get("methods", [])
                    new_permissions.append(token_pb2.PermissionsByVisibility(
                        infra=token_pb2.InfraPermissions(
                            methods=methods,
                        ),
                    ))
                    new_methods.extend(methods)
                if permission.get("admin"):
                    methods = permission.get("admin").get("methods", [])
                    new_permissions.append(token_pb2.PermissionsByVisibility(
                        admin=token_pb2.AdminPermissions(
                            methods=methods,
                        ),
                    ))
                    new_methods.extend(methods)
                if permission.get("public"):
                    methods = permission.get("public").get("methods", [])
                    new_permissions.append(token_pb2.PermissionsByVisibility(
                        public=token_pb2.PublicPermissions(
                            methods=methods,
                        ),
                    ))
                    new_methods.extend(methods)
                if permission.get("project"):
                    methods = permission.get("project").get("methods", [])
                    new_permissions.append(token_pb2.PermissionsByVisibility(
                        project=token_pb2.ProjectPermissions(
                            project=permission.get("project").get("project"),
                            methods=methods,
                        ),
                    ))
                    new_methods.extend(methods)
                if permission.get("tenant"):
                    methods = permission.get("tenant").get("methods", [])
                    new_permissions.append(token_pb2.PermissionsByVisibility(
                        tenant=token_pb2.TenantPermissions(
                            login=permission.get("tenant").get("login"),
                            methods=methods,
                        ),
                    ))
                    new_methods.extend(methods)
                if permission.get("machine"):
                    methods = permission.get("machine").get("methods", [])
                    new_permissions.append(token_pb2.PermissionsByVisibility(
                        machine=token_pb2.MachinePermissions(
                            uuid=permission.get("machine").get("uuid"),
                            methods=methods,
                        ),
                    ))
                    new_methods.extend(methods)

            if set(old_methods) != set(new_methods):
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

        if self._labels != None:
            labels = self._labels | {
                V2_ANSIBLE_CI_IDENTIFIER_KEY: self._identifier,
                V2_ANSIBLE_CI_MANAGED_KEY: V2_ANSIBLE_CI_MANAGED_VALUE,
            }

            if self._token.meta.labels.labels != labels:
                self.changed = True
                r.labels.CopyFrom(common_pb2.UpdateLabels(
                    replace=common_pb2.Labels(labels=labels)
                ))

        if self.changed:
            try:
                resp = self._client.apiv2().token().update(request=r, headers=self._headers)
                self._token = resp.token
            except ConnectError as e:
                self._module.fail_json(
                    msg="request to metal-apiserver failed", error=str(e))

    def _create(self):
        labels = self._labels if self._labels else dict()
        labels = labels | {
            V2_ANSIBLE_CI_IDENTIFIER_KEY: self._identifier,
            V2_ANSIBLE_CI_MANAGED_KEY: V2_ANSIBLE_CI_MANAGED_VALUE,
        }

        r = token_pb2.TokenServiceCreateRequest(
            description=self._description,
            labels=common_pb2.Labels(labels=labels),
        )

        if self._description:
            r.description = self._description

        if self._expires:
            r.expires = self._expires

        for permission in self._permissions:
            if permission.get("self"):
                r.permissions.append(token_pb2.PermissionsByVisibility(
                    self=token_pb2.SelfPermissions(
                        methods=permission.get("self").get("methods", [])
                    ),
                ))
            if permission.get("infra"):
                r.permissions.append(token_pb2.PermissionsByVisibility(
                    infra=token_pb2.InfraPermissions(
                        methods=permission.get("infra").get("methods", [])
                    ),
                ))
            if permission.get("admin"):
                r.permissions.append(token_pb2.PermissionsByVisibility(
                    admin=token_pb2.AdminPermissions(
                        methods=permission.get("admin").get("methods", [])
                    ),
                ))
            if permission.get("public"):
                r.permissions.append(token_pb2.PermissionsByVisibility(
                    public=token_pb2.PublicPermissions(
                        methods=permission.get("public").get("methods", [])
                    ),
                ))
            if permission.get("project"):
                r.permissions.append(token_pb2.PermissionsByVisibility(
                    project=token_pb2.ProjectPermissions(
                        project=permission.get("project").get("project"),
                        methods=permission.get("project").get("methods", [])
                    ),
                ))
            if permission.get("tenant"):
                r.permissions.append(token_pb2.PermissionsByVisibility(
                    tenant=token_pb2.TenantPermissions(
                        login=permission.get("tenant").get("login"),
                        methods=permission.get("tenant").get("methods", [])
                    ),
                ))
            if permission.get("machine"):
                r.permissions.append(token_pb2.PermissionsByVisibility(
                    machine=token_pb2.MachinePermissions(
                        uuid=permission.get("machine").get("uuid"),
                        methods=permission.get("machine").get("methods", [])
                    ),
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
            resp = self._client.apiv2().token().create(request=r, headers=self._headers)
            self._token = resp.token
            self._secret = resp.secret
        except ConnectError as e:
            self._module.fail_json(
                msg="request to metal-apiserver failed", error=str(e))

        self._uuid = self._token.uuid

    def _delete(self):
        try:
            self._client.apiv2().token().revoke(request=token_pb2.TokenServiceRevokeRequest(
                uuid=self._uuid,
            ), headers=self._headers)
        except ConnectError as e:
            self._module.fail_json(
                msg="request to metal-apiserver failed", error=str(e))


def main():
    argument_spec = V2_AUTH_SPEC.copy()
    argument_spec.update(dict(
        identifier=dict(type='str', required=True),
        use_latest_identifier=dict(type='bool', default=False),
        description=dict(type='str', required=False),
        expires=dict(type='str', required=False),
        permissions=dict(type='list', required=False, elements='dict', options=dict(
            self=dict(type='dict', options=dict(
                methods=dict(type='list', elements='str'),)),
            admin=dict(type='dict', options=dict(
                methods=dict(type='list', elements='str'),)),
            infra=dict(type='dict', options=dict(
                methods=dict(type='list', elements='str'),)),
            public=dict(type='dict', options=dict(
                methods=dict(type='list', elements='str'),)),
            project=dict(type='dict', options=dict(
                methods=dict(type='list', elements='str'), project=dict(type='str', required=True),)),
            tenant=dict(type='dict', options=dict(
                methods=dict(type='list', elements='str'), login=dict(type='str', required=True),)),
            machine=dict(type='dict', options=dict(
                methods=dict(type='list', elements='str'), uuid=dict(type='str', required=True),)),
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
        id=instance._uuid,
    )

    if instance._token:
        result['token'] = MessageToDict(instance._token)
    if instance._secret:
        result['secret'] = instance._secret

    module.exit_json(**result)


if __name__ == '__main__':
    main()
