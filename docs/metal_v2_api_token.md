# metal_v2_api_token

A module to manage api token entities.

## Synopsis

- Manages api token entities in the metal-apiserver.

- Requires metal-stack-api to be installed.

- Authentication can be provided via the *api_url* and *api_token* options or the METAL_APIV2_URL and METAL_APIV2_TOKEN environment variables.

- An optional *api_timeout* can be set to limit the request duration.


## Requirements

- [metal-stack-api](https://pypi.org/project/metal-stack-api/)


## Parameters

| Parameter | Type | Required | Default | Choices | Comments |
|-----------|------|----------|---------|---------|----------|
| `admin_role` | str | no |  |  | The admin role for this token. |
| `description` | str | no |  |  | The description of the token. |
| `expires` | str | no |  |  | The duration until this token expires. This field cannot be updated and is only used on token creation. |
| `identifier` | str | yes |  |  | A resource identifier for resources that have auto-generated uuids. The identifier gets stored in the resource labels. With this, the module can figure out if the resource already exists using the identifier label. If multiple resources with the same identifier label are found, the module will throw an error. |
| `labels` | str | no |  |  | The labels of the token. Set to empty dict in order to clean existing. |
| `permissions` | str | no |  |  | A list of api-method permissions. |
| `project_roles` | str | no |  |  | A map of project identifiers to tenant roles. |
| `state` | str | no | `present` | `absent`, `present` | Assert the state of the token. Use `present` to create or update a token and `absent` to delete it. |
| `tenant_roles` | str | no |  |  | A map of tenant identifiers to tenant roles. |
| `use_latest_identifier` | str | no | `false` |  | If set to true and multiple resources with the same identifier label are found, the module acts on the latest created resource. If set to false (default) and multiple resources match, the module will fail with an error. |



## Return Values

| Key | Type | Returned | Description | Sample |
|-----|------|----------|-------------|--------|
| `id` | str | ifexisted but not returned on deletion | token id | ae6834bd-1ca8-4d22-b38a-8a7c771c06b0 |
| `secret` | str | oncreation | the token secret | <a-secret-jwt-token> |
| `token` | dict | ifexisted but not returned on deletion | the token response | [sample_token](#sample-sample_token) |

#### Sample sample_token

```json
{
  "expires": "2026-07-18T11:54:36.591697440Z",
  "issuedAt": "2026-07-17T11:54:36.591697440Z",
  "meta": {
    "createdAt": "2026-07-17T11:54:36.591697440Z",
    "labels": {
      "labels": {
        "ci.metal-stack.io/id": "token-refresh",
        "ci.metal-stack.io/manager": "ansible"
      }
    }
  },
  "permissions": [
    {
      "methods": [
        "/metalstack.api.v2.TokenService/Refresh"
      ]
    }
  ],
  "tokenType": "TOKEN_TYPE_API",
  "user": "metal-stack",
  "uuid": "ae6834bd-1ca8-4d22-b38a-8a7c771c06b0"
}
```



**Version added:** 2.18


## Examples

```yaml
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
```


## Authors

- metal-stack



*status: stableinterface, supported_by: community*
