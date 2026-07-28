#!/usr/bin/python
# -*- coding: utf-8 -*-

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.metal_v2 import BaseMetalV2Resource, parse_delta


try:
    from connectrpc.errors import ConnectError
    from google.protobuf.json_format import MessageToDict

    from metalstack.api.v2 import common_pb2, token_pb2
    from metalstack.admin.v2 import token_pb2 as admin_token_pb2
except ImportError:
    pass


ANSIBLE_METADATA = {
    'metadata_version': '0.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: metal_v2_admin_token

short_description: A module to manage api token entities.

version_added: "2.18"

description:
    - Manages api token entities in the metal-apiserver.
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
    description:
        description:
            - The description of the token.
        required: false
    user:
        description:
            - The user to whom the created token will belong.
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
    labels:
        description:
            - The labels of the token.
            - Set to empty dict in order to clean existing.
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
  metal_v2_admin_token:
    identifier: metal-bmc
    user: metal-bmc
    description: an infra component token
    permissions:
    - subject: '*'
      methods:
        - /metalstack.infra.v2.BMCService/UpdateBMCInfo
        - /metalstack.api.v2.TokenService/Refresh

- name: revoke a token
  metal_v2_admin_token:
    identifier: metal-bmc
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
    description: for metal-bmc
    expires: '2025-01-01T14:00:00.00000000Z'
    issuedAt: '2025-01-01T12:00:00.00000000Z'
    permissions:
    -   methods:
        - /metalstack.infra.v2.BMCService/UpdateBMCInfo
        - /metalstack.api.v2.TokenService/Refresh
        subject: '*'
    tokenType: TOKEN_TYPE_API
    user: user@oidc
    uuid: ae6834bd-1ca8-4d22-b38a-8a7c771c06b0
'''


class Instance(BaseMetalV2Resource):
    def __init__(self, module):
        super().__init__(module)
        self._token: token_pb2.Token = None
        self._uuid = None
        self._secret = None
        self._user = module.params.get('user')
        self._description = module.params.get('description')
        self._expires = parse_delta(module.params.get(
            'expires')) if module.params.get('expires') else None
        self._project_roles = module.params.get('project_roles')
        self._tenant_roles = module.params.get('tenant_roles')
        self._admin_role = module.params.get('admin_role')
        self._permissions = module.params.get('permissions') or []

    def _get_resource(self):
        return self._token

    def _find(self):
        r = admin_token_pb2.TokenServiceListRequest(
            query=token_pb2.TokenQuery(
                labels=common_pb2.Labels(
                    labels={
                        self.V2_ANSIBLE_CI_IDENTIFIER_KEY: self._identifier,
                        self.V2_ANSIBLE_CI_MANAGED_KEY: self.V2_ANSIBLE_CI_MANAGED_VALUE,
                    },
                ),
            ),
        )

        try:
            resp = self._client.adminv2().token().list(request=r, headers=self._headers)
        except ConnectError as e:
            self._module.fail_json(
                msg="request to metal-apiserver failed", error=str(e))
            return

        self._token = self._get_latest_resource(resp.tokens)
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

        if self._user and self._token.user != self._user:
            self._module.fail_json(
                msg=f"token belongs to user {self._token.user}, it cannot be changed to user {self._user}")
            return

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
            labels = self._build_labels()

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
        labels = self._build_labels()

        r = token_pb2.TokenServiceCreateRequest(
            labels=common_pb2.Labels(
                labels=labels
            )
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
            resp = self._client.adminv2().token().create(request=admin_token_pb2.TokenServiceCreateRequest(
                user=self._user,
                token_create_request=r,
            ), headers=self._headers)
            self._token = resp.token
            self._secret = resp.secret

        except ConnectError as e:
            self._module.fail_json(
                msg="request to metal-apiserver failed", error=str(e))

        self._uuid = self._token.uuid

    def _delete(self):
        try:
            self._client.adminv2().token().revoke(request=admin_token_pb2.TokenServiceRevokeRequest(
                user=self._user,
                uuid=self._uuid,
            ), headers=self._headers)

        except ConnectError as e:
            self._module.fail_json(
                msg="request to metal-apiserver failed", error=str(e))


def main():
    module = AnsibleModule(
        argument_spec=BaseMetalV2Resource._create_argument_spec(dict(
            user=dict(type='str', required=True),
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
        )),
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
