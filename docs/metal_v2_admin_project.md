# metal_v2_admin_project

A module to manage metal project entities.

## Synopsis

- Manages project entities in the metal-apiserver.

- Requires metal-stack-api to be installed.

- Authentication can be provided via the *api_url* and *api_token* options or the METAL_APIV2_URL and METAL_APIV2_TOKEN environment variables.

- An optional *api_timeout* can be set to limit the request duration.


## Requirements

- [metal-stack-api](https://pypi.org/project/metal-stack-api/)


## Parameters

| Parameter | Type | Required | Default | Choices | Comments |
|-----------|------|----------|---------|---------|----------|
| `avatar_url` | str | no |  |  | The avatar url of the project. |
| `description` | str | yes |  |  | The description of the project. |
| `identifier` | str | yes |  |  | A resource identifier for resources that have auto-generated uuids. The identifier gets stored in the resource labels. With this, the module can figure out if the resource already exists using the identifier label. If multiple resources with the same identifier label are found, the module will throw an error. |
| `labels` | str | no |  |  | The labels of the project. Set to empty dict in order to clean existing. |
| `name` | str | yes |  |  | The name of the project. |
| `state` | str | no | `present` | `absent`, `present` | Assert the state of the project. Use `present` to create or update a project and `absent` to delete it. |
| `tenant` | str | yes |  |  | The tenant of the project. |
| `use_latest_identifier` | str | no | `false` |  | If set to true and multiple resources with the same identifier label are found, the module acts on the latest created resource. If set to false (default) and multiple resources match, the module will fail with an error. |



## Return Values

| Key | Type | Returned | Description | Sample |
|-----|------|----------|-------------|--------|
| `id` | str | ifexisted | project id | 3e977e81-6ab5-4f28-b608-e7e94d62efb7 |
| `project` | dict | ifexisted | project response | [sample_project](#sample-sample_project) |

#### Sample sample_project

```json
{
  "avatarUrl": "http://test",
  "description": "test project",
  "meta": {
    "createdAt": "2025-01-01T12:00:00.00000000Z",
    "labels": {
      "labels": {
        "ci.metal-stack.io/id": "test",
        "ci.metal-stack.io/manager": "ansible"
      }
    }
  },
  "name": "test",
  "tenant": "user@oidc",
  "uuid": "3e977e81-6ab5-4f28-b608-e7e94d62efb7"
}
```



**Version added:** 2.18


## Examples

```yaml
- name: create a project
  metal_v2_admin_project:
    identifier: test
    name: my-project
    description: test project
    tenant: user@oidc
    avatar_url: http://test

- name: delete a project
  metal_v2_admin_project:
    identifier: test
    state: absent
```


## Authors

- metal-stack



*status: stableinterface, supported_by: community*
