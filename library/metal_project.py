#!/usr/bin/python
# -*- coding: utf-8 -*-

try:
    from metal_python.api import ProjectApi
    from metal_python import models
    from metal_python import rest

    METAL_PYTHON_AVAILABLE = True
except ImportError:
    METAL_PYTHON_AVAILABLE = False

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.metal import AUTH_SPEC, ANSIBLE_CI_MANAGED_LABEL, ANSIBLE_CI_MANAGED_KEY, \
    ANSIBLE_CI_MANAGED_VALUE, init_driver_for_module

ANSIBLE_METADATA = {
    'metadata_version': '0.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: metal_project

short_description: A module to manage metal project entities

version_added: "2.8"

description:
    - Manages project entities in the metal-api.
    - Requires metal_python to be installed.

options:
    name:
        description:
            - >-
              The name of the project, which must be globally unique.
              Otherwise, the module cannot figure out if the project was already created or not.
        required: true
    description:
        description:
            - The description of the project.
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
- name: allocate a project
  metal_project:
    name: my-project
    description: "my project"
    labels:
      - my-project-label

- name: free a project
  metal_project:
    name: my-project
    state: absent
'''

RETURN = '''
id:
    description:
        - project id
    returned: always
    type: str
    sample: 3e977e81-6ab5-4f28-b608-e7e94d62efb7
'''


class Instance(object):
    def __init__(self, module):
        if not METAL_PYTHON_AVAILABLE:
            raise RuntimeError("metal_python must be installed")

        self._module = module
        self.changed = False
        self._project = None
        self.id = None
        self._name = module.params['name']
        self._description = module.params.get('description')
        self._tenant = module.params.get('tenant')
        self._labels = module.params.get('labels')
        self._state = module.params.get('state')
        self._driver = init_driver_for_module(self._module)
        self._api_client = ProjectApi(api_client=self._driver.client)

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
        r = models.V1ProjectFindRequest(name=self._name)
        try:
            projects = self._api_client.find_projects(r)
        except rest.ApiException as e:
            self._module.fail_json(msg="request to metal-api failed", error=str(e))
            return

        if projects is None:
            return

        if len(projects) > 1:
            self._module.fail_json(
                msg="project name is not globally unique, which is required when "
                    "using this module", name=self._name)
        elif len(projects) == 1:
            self._project = projects[0]
            self.id = self._project.meta.id

    def _update(self):
        meta = models.V1Meta(id=self.id)
        r = models.V1ProjectUpdateRequest(description=None, meta=meta, name=None, quotas=None, tenant_id=None)

        if self._project.description != self._description:
            self.changed = True
            r.description = self._description

        if self._project.tenant_id != self._tenant:
            self.changed = True
            r.tenant_id = self._tenant

        if self._project.meta.labels != self._labels:
            self.changed = True
            meta.labels = self._labels

        if self.changed:
            try:
                self._project = self._api_client.update_project(r)
            except rest.ApiException as e:
                self._module.fail_json(msg="request to metal-api failed", error=str(e))

    def _create(self):
        annotations = ANSIBLE_CI_MANAGED_LABEL

        r = models.V1ProjectCreateRequest(description=self._description,
                                          meta=models.V1Meta(
                                              annotations=annotations,
                                              labels=self._labels,
                                          ),
                                          name=self._name,
                                          tenant_id=self._tenant)

        try:
            self._project = self._api_client.create_project(r)
        except rest.ApiException as e:
            self._module.fail_json(msg="request to metal-api failed", error=str(e))

        self.id = self._project.meta.id

    def _delete(self):
        if self._project.meta.annotations.get(ANSIBLE_CI_MANAGED_KEY) != ANSIBLE_CI_MANAGED_VALUE:
            self._module.fail_json(msg="entity does not have label attached: %s" % ANSIBLE_CI_MANAGED_LABEL,
                                   name=self._name)

        try:
            self._project = self._api_client.delete_project(self.id)
        except rest.ApiException as e:
            self._module.fail_json(msg="request to metal-api failed", error=str(e))

        self.id = self._project.meta.id


def main():
    argument_spec = AUTH_SPEC.copy()
    argument_spec.update(dict(
        name=dict(type='str', required=True),
        tenant=dict(type='str', required=False),
        description=dict(type='str', required=False),
        labels=dict(type='list', required=False),
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
