#!/usr/bin/python
# -*- coding: utf-8 -*-

from datetime import datetime
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.metal_v2 import V2_AUTH_SPEC, V2_ANSIBLE_CI_MANAGED_KEY, V2_ANSIBLE_CI_MANAGED_VALUE, V2_ANSIBLE_CI_IDENTIFIER_KEY, init_client_for_module


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
    identifier:
        description:
            - A resource identifier for resources that have auto-generated uuids.
              The identifier gets stored in the resource labels.
              With this, the module can figure out if the resource already exists using the identifier label.
              If multiple resources with the identifier label are found, the module acts on the latest created resource.
        required: true
    name:
        description:
            - The name of the project.
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
        - The labels of the project.
        - Set to empty dict in order to clean existing.
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
    identifier: test
    name: my-project
    description: test project
    tenant: user@oidc
    avatar_url: http://test

- name: delete a project
  metal_v2_project:
    identifier: test
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
                    ci.metal-stack.io/id: test
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
        self._identifier = module.params.get('identifier')
        self._description = module.params.get('description')
        self._avatar_url = module.params.get('avatar_url')
        self._tenant = module.params.get('tenant')
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
            query=project_pb2.ProjectQuery(
                labels=common_pb2.Labels(
                    labels={
                        V2_ANSIBLE_CI_IDENTIFIER_KEY: self._identifier,
                        V2_ANSIBLE_CI_MANAGED_KEY: V2_ANSIBLE_CI_MANAGED_VALUE,
                    },
                ),
            ),
        )

        try:
            resp = self._client.apiv2().project().list(request=r, headers=self._headers)
        except ConnectError as e:
            self._module.fail_json(
                msg="request to metal-apiserver failed", error=str(e))
            return

        projects = resp.projects
        if projects is None:
            return

        latest_created = None

        for project in projects:
            if latest_created is None:
                latest_created = project
                continue

            if project.meta.created_at.ToDatetime() > latest_created.meta.created_at.ToDatetime():
                latest_created = project

        self._project = latest_created
        self._uuid = self._project.uuid

    def _update(self):
        r = project_pb2.ProjectServiceUpdateRequest(
            project=self._uuid,
            update_meta=common_pb2.UpdateMeta(
                locking_strategy=common_pb2.OPTIMISTIC_LOCKING_STRATEGY_CLIENT,
                updated_at=self._project.meta.updated_at,
            ),
        )

        if self._name and self._project.name != self._name:
            self.changed = True
            r.name = self._name
        if self._description and self._project.description != self._description:
            self.changed = True
            r.description = self._description
        if self._avatar_url and self._project.avatar_url != self._avatar_url:
            self.changed = True
            r.avatar_url = self._avatar_url

        if self._tenant and self._project.tenant != self._tenant:
            self._module.fail_json(
                msg=f"project belongs to tenant {self._project.tenant}, it cannot be changed to tenant {self._tenant}")
            return

        if self._labels != None:
            labels = self._labels | {
                V2_ANSIBLE_CI_IDENTIFIER_KEY: self._identifier,
                V2_ANSIBLE_CI_MANAGED_KEY: V2_ANSIBLE_CI_MANAGED_VALUE,
            }

            if self._project.meta.labels.labels != labels:
                self.changed = True
                r.labels.CopyFrom(common_pb2.UpdateLabels(
                    replace=common_pb2.Labels(labels=labels)
                ))

        if self.changed:
            try:
                resp = self._client.apiv2().project().update(request=r, headers=self._headers)
                self._project = resp.project
            except ConnectError as e:
                self._module.fail_json(
                    msg="request to metal-apiserver failed", error=str(e))

    def _create(self):
        labels = self._labels if self._labels else dict()
        labels = labels | {
            V2_ANSIBLE_CI_IDENTIFIER_KEY: self._identifier,
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

        try:
            resp = self._client.apiv2().project().create(request=r, headers=self._headers)
            self._project = resp.project
        except ConnectError as e:
            self._module.fail_json(
                msg="request to metal-apiserver failed", error=str(e))

        self._uuid = self._project.uuid

    def _delete(self):
        try:
            resp = self._client.apiv2().project().delete(project_pb2.ProjectServiceDeleteRequest(
                project=self._uuid,
            ), headers=self._headers)
            self._project = resp.project
        except ConnectError as e:
            self._module.fail_json(
                msg="request to metal-apiserver failed", error=str(e))


def main():
    argument_spec = V2_AUTH_SPEC.copy()
    argument_spec.update(dict(
        identifier=dict(type='str', required=True),
        name=dict(type='str', required=True),
        tenant=dict(type='str', required=True),
        description=dict(type='str', required=True),
        avatar_url=dict(type='str', required=False),
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

    if instance._project:
        result['project'] = MessageToDict(instance._project)

    module.exit_json(**result)


if __name__ == '__main__':
    main()
