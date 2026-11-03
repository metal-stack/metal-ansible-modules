# metal_v2_tenant

A module to manage metal tenant entities.

## Synopsis

- Manages tenant entities in the metal-apiserver.

- Requires metal-stack-api to be installed.

- Authentication can be provided via the *api_url* and *api_token* options or the METAL_APIV2_URL and METAL_APIV2_TOKEN environment variables.

- An optional *api_timeout* can be set to limit the request duration.


## Requirements

- [metal-stack-api](https://pypi.org/project/metal-stack-api/)


## Parameters

| Parameter | Type | Required | Default | Choices | Comments |
|-----------|------|----------|---------|---------|----------|
| `avatar_url` | str | no |  |  | The avatar url of the tenant. |
| `description` | str | yes |  |  | The description of the tenant. |
| `email` | str | no |  |  | The email of the tenant. |
| `identifier` | str | yes |  |  | A resource identifier for resources that have auto-generated uuids. The identifier gets stored in the resource labels. With this, the module can figure out if the resource already exists using the identifier label. If multiple resources with the same identifier label are found, the module will throw an error. |
| `labels` | str | no |  |  | The labels of the tenant. Set to empty dict in order to clean existing. |
| `name` | str | yes |  |  | The name of the tenant. |
| `state` | str | no | `present` | `absent`, `present` | Assert the state of the tenant. Use `present` to create or update a tenant and `absent` to delete it. |
| `use_latest_identifier` | str | no | `false` |  | If set to true and multiple resources with the same identifier label are found, the module acts on the latest created resource. If set to false (default) and multiple resources match, the module will fail with an error. |



## Return Values

| Key | Type | Returned | Description | Sample |
|-----|------|----------|-------------|--------|
| `id` | str | ifexisted | tenant id | b5bc5d9f-3ade-4eac-bb8c-eb309045151f |
| `tenant` | dict | ifexisted | tenant response | [sample_tenant](#sample-sample_tenant) |

#### Sample sample_tenant

```json
{
  "avatarUrl": "http://test",
  "createdBy": "user@oidc",
  "description": "test tenant",
  "email": "admin@metal-stack.io",
  "login": "b5bc5d9f-3ade-4eac-bb8c-eb309045151f",
  "meta": {
    "createdAt": "2025-01-01T12:00:00.00000000Z",
    "labels": {
      "labels": {
        "ci.metal-stack.io/id": "test",
        "ci.metal-stack.io/manager": "ansible"
      }
    }
  },
  "name": "test"
}
```



**Version added:** 2.18


## Examples

```yaml
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
```


## Authors

- metal-stack



*status: stableinterface, supported_by: community*
