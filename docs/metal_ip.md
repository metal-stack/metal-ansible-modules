# metal_ip

A module to manage metal ip entities

## Synopsis

- Manages ip entities in the metal-api.

- Requires metal_python to be installed.


## Requirements

- [metal-python](https://pypi.org/project/metal-python/)


## Parameters

| Parameter | Type | Required | Default | Choices | Comments |
|-----------|------|----------|---------|---------|----------|
| `description` | str | no |  |  | The description of the ip. |
| `ip` | str | no |  |  | The ip address to allocate. |
| `name` | str | no |  |  | The name of the ip, which must be unique within a project  (in case ip is not provided). Otherwise, the module cannot figure out if the ip was already created or not. |
| `network` | str | no |  |  | The network to allocate the ip in. |
| `project` | str | no |  |  | The project of the ip. |
| `state` | str | no | `present` | `absent`, `present` | Assert the state of the ip. Use `present` to create or update a ip and `absent` to delete it. |
| `type` | str | no | `static` | `static`, `ephemeral` | The type of the ip. |



## Return Values

| Key | Type | Returned | Description | Sample |
|-----|------|----------|-------------|--------|
| `ip` | str | always | ip address | 212.34.83.13 |




**Version added:** 2.8


## Examples

```yaml
- name: allocate a specific ip
  metal_ip:
    ip: 212.34.83.13
    name: my-ip
    description: "my static ip"
    network: internet-fra-equ01
    type: static
    project: 9ec6882a-cd94-42a7-b667-ffaed43557c7

- name: allocate a random ip
  metal_ip:
    name: my-ip
    description: "my random ip"
    network: internet-fra-equ01
    type: static
    project: 9ec6882a-cd94-42a7-b667-ffaed43557c7

- name: free an ip
  metal_ip:
    ip: 212.34.83.13
    state: absent
```


## Authors

- metal-stack



*status: stableinterface, supported_by: community*
