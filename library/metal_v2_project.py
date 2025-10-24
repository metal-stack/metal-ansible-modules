#!/usr/bin/python
# -*- coding: utf-8 -*-

from datetime import datetime
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.metal_v2 import V2_AUTH_SPEC, V2_ANSIBLE_CI_MANAGED_KEY, V2_ANSIBLE_CI_MANAGED_VALUE, init_client_for_module


try:
    from connectrpc.errors import ConnectError
    from google.protobuf.json_format import MessageToDict

    from metalstack.api.v2 import common_pb2, project_pb2
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
module: metal_v2_project

short_description: A module to manage metal project entities.

version_added: "2.18"

description:
    - Manages project entities in the metal-apiserver.
    - Requires metal-stack-api to be installed.

options:
    name:
        description:
            - >-
              The name of the project, which must be unique in the tenant.
              Otherwise, the module cannot figure out if the project was already created or not.
        required: true
    description:
        description:
            - The description of the project.
        required: true
    avatar_url:
        description:
            - The avatar url of the project.
        required: false
    tenant:
        tenant:
            - The tenant of the project.
        required: false
    labels:
        description:
            - The labels of the project.
        required: false
    state:
        description:
          - Assert the state of the project.
          - >-
            Use C(present) to create or update a project and C(absent) to
            delete it.
        default: present
        choices:
          - absent
          - present

author:
    - metal-stack
'''

EXAMPLES = '''
- name: create a project
  metal_v2_project:
    name: my-project
    description: test project
    tenant: user@oidc
    avatar_url: http://test

- name: free a project
  metal_v2_project:
    name: my-project
    state: absent
'''

RETURN = '''
id:
    description:
        - project id
    returned: ifexisted
    type: str
    sample: 3e977e81-6ab5-4f28-b608-e7e94d62efb7
project:
    description:
        - project response
    returned: ifexisted
    type: dict
    sample:
        avatarUrl: http://test
        description: test project
        meta:
            createdAt: '2025-01-01T12:00:00.00000000Z'
            labels:
                labels:
                    ci.metal-stack.io/manager: ansible
        name: test
        tenant: user@oidc
        uuid: 3e977e81-6ab5-4f28-b608-e7e94d62efb7
'''


class Instance(object):
    def __init__(self, module):
        if not METAL_STACK_API_AVAILABLE:
            raise RuntimeError("metal-stack-api must be installed")

        self._module = module
        self.changed = False
        self._project: project_pb2.Project = None
        self._uuid = None
        self._name = module.params['name']
        self._description = module.params.get('description')
        self._avatar_url = module.params.get('avatar_url')
        self._tenant = module.params.get('tenant')
        self._labels = module.params.get('labels')
        self._state = module.params.get('state')
        self._client: apiclient.Client = init_client_for_module(module)

    def run(self):
        if self._module.check_mode:
            return

        self._find()

        if self._state == "present":
            if self._project:
                self._update()
                return

            self._create()
            self.changed = True

        elif self._state == "absent":
            if self._project:
                self._delete()
                self.changed = True

    def _find(self):
        r = project_pb2.ProjectServiceListRequest(
            name=self._name,
            tenant=self._tenant,
        )

        try:
            resp = self._client.apiv2().project().list(request=r)
        except ConnectError as e:
            self._module.fail_json(
                msg="request to metal-apiserver failed", error=str(e))
            return

        projects = resp.projects

        if projects is None:
            return

        if len(projects) > 1:
            self._module.fail_json(
                msg="project name is not unique within the tenant, which is required when "
                    "using this module", name=self._name)
        elif len(projects) == 1:
            self._project = projects[0]
            self._uuid = self._project.uuid

    def _update(self):
        r = project_pb2.ProjectServiceUpdateRequest(
            project=self._uuid,
            update_meta=common_pb2.UpdateMeta(
                locking_strategy=common_pb2.OPTIMISTIC_LOCKING_STRATEGY_CLIENT,
                updated_at=datetime.now(),
            ),
        )

        if not self._project.meta.labels.labels.get(V2_ANSIBLE_CI_MANAGED_KEY, "") == V2_ANSIBLE_CI_MANAGED_VALUE:
            self._module.fail_json(
                msg=f"refusing to update because label is not present on entity: {V2_ANSIBLE_CI_MANAGED_KEY}={V2_ANSIBLE_CI_MANAGED_VALUE}")
            return

        if self._description and self._project.description != self._description:
            self.changed = True
            r.description = self._description

        if self._avatar_url and self._project.avatar_url != self._avatar_url:
            self.changed = True
            r.avatar_url = self._avatar_url

        if self._labels:
            self._labels[V2_ANSIBLE_CI_MANAGED_KEY] = V2_ANSIBLE_CI_MANAGED_VALUE

            if self._project.meta.labels != self._labels:
                self.changed = True
                r.labels = self._labels

        if self.changed:
            try:
                resp = self._client.apiv2().project().update(r)
                self._project = resp.project
            except ConnectError as e:
                self._module.fail_json(
                    msg="request to metal-apiserver failed", error=str(e))

    def _create(self):
        labels = {
            V2_ANSIBLE_CI_MANAGED_KEY: V2_ANSIBLE_CI_MANAGED_VALUE,
        }

        r = project_pb2.ProjectServiceCreateRequest(
            login=self._tenant,
            name=self._name,
            description=self._description,
            labels=common_pb2.Labels(labels=labels),
        )

        if self._avatar_url:
            r.avatar_url = self._avatar_url
        if self._labels:
            r.labels = common_pb2.Labels(labels=self._labels | labels)

        try:
            resp = self._client.apiv2().project().create(r)
            self._project = resp.project
        except ConnectError as e:
            self._module.fail_json(
                msg="request to metal-apiserver failed", error=str(e))

        self._uuid = self._project.uuid

    def _delete(self):
        if not self._project.meta.labels.labels.get(V2_ANSIBLE_CI_MANAGED_KEY, "") == V2_ANSIBLE_CI_MANAGED_VALUE:
            self._module.fail_json(
                msg=f"refusing to delete because label is not present on entity: {V2_ANSIBLE_CI_MANAGED_KEY}={V2_ANSIBLE_CI_MANAGED_VALUE}")
            return

        try:
            resp = self._client.apiv2().project().delete(project_pb2.ProjectServiceDeleteRequest(
                project=self._uuid,
            ))
            self._project = resp.project
        except ConnectError as e:
            self._module.fail_json(
                msg="request to metal-apiserver failed", error=str(e))


def main():
    argument_spec = V2_AUTH_SPEC.copy()
    argument_spec.update(dict(
        name=dict(type='str', required=True),
        tenant=dict(type='str', required=True),
        description=dict(type='str', required=True),
        avatar_url=dict(type='str', required=False),
        labels=dict(type='list', required=False),
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

    if instance._project:
        result['project'] = MessageToDict(instance._project)

    module.exit_json(**result)


if __name__ == '__main__':
    main()
