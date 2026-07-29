# metal_project

A module to manage metal project entities

## Synopsis

- Manages project entities in the metal-api.

- Requires metal_python to be installed.


## Requirements

- [metal-python](https://pypi.org/project/metal-python/)


## Parameters

| Parameter | Type | Required | Default | Choices | Comments |
|-----------|------|----------|---------|---------|----------|
| `description` | str | no |  |  | The description of the project. |
| `labels` | str | no |  |  | The labels of the project. |
| `name` | str | yes |  |  | The name of the project, which must be globally unique. Otherwise, the module cannot figure out if the project was already created or not. |
| `state` | str | no | `present` | `absent`, `present` | Assert the state of the project. Use `present` to create or update a project and `absent` to delete it. |
| `tenant` | str | no |  |  |  |



## Return Values

| Key | Type | Returned | Description | Sample |
|-----|------|----------|-------------|--------|
| `id` | str | always | project id | 3e977e81-6ab5-4f28-b608-e7e94d62efb7 |




**Version added:** 2.8


## Examples

```yaml
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
```


## Authors

- metal-stack



*status: stableinterface, supported_by: community*
