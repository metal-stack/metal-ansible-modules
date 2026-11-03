# metal_network

A module to manage metal network entities

## Synopsis

- Manages network entities in the metal-api.

- Requires metal_python to be installed.


## Requirements

- [metal-python](https://pypi.org/project/metal-python/)


## Parameters

| Parameter | Type | Required | Default | Choices | Comments |
|-----------|------|----------|---------|---------|----------|
| `description` | str | no |  |  | The description of the network. |
| `labels` | str | no |  |  | The labels of the network. |
| `name` | str | yes |  |  | The name of the network, which must be unique within a project and partition. Otherwise, the module cannot figure out if the network was already created or not. |
| `partition` | str | yes |  |  | The partition to allocate the network in. |
| `project` | str | yes |  |  | The project of the network. |
| `state` | str | no | `present` | `absent`, `present` | Assert the state of the network. Use `present` to create or update a network and `absent` to delete it. |



## Return Values

| Key | Type | Returned | Description | Sample |
|-----|------|----------|-------------|--------|
| `id` | str | always | network id | 3e977e81-6ab5-4f28-b608-e7e94d62efb7 |
| `prefixes` | list | always | array of network prefixes | [sample_prefixes](#sample-sample_prefixes) |

#### Sample sample_prefixes

```json
[
  "10.0.112.0/22"
]
```



**Version added:** 2.8


## Examples

```yaml
- name: allocate a network
  metal_network:
    name: my-network
    description: "my network"
    partition: fra-equ01
    project: 9ec6882a-cd94-42a7-b667-ffaed43557c7

- name: free a network
  metal_network:
    name: my-network
    project: 6df6a987-922d-4c36-8cd9-5edbd1584f7a
    partition: fra-equ01
    state: absent
```


## Authors

- metal-stack



*status: stableinterface, supported_by: community*
