# metal_machine

A module to manage metal machine entities

## Synopsis

- Manages machine entities in the metal-api.

- Requires metal_python to be installed.


## Requirements

- [metal-python](https://pypi.org/project/metal-python/)


## Parameters

| Parameter | Type | Required | Default | Choices | Comments |
|-----------|------|----------|---------|---------|----------|
| `description` | str | no |  |  | The description of the machine. |
| `filesystemlayout` | str | no |  |  | The file system layout to use for the machine allocation. |
| `hostname` | str | no |  |  | The hostname of the machine. |
| `id` | str | no |  |  | The id of the machine, user for specific machine allocation. |
| `image` | str | no |  |  | The image of the machine. |
| `ips` | str | no |  |  | The ips of the machine. |
| `name` | str | no |  |  | The name of the machine, which must be unique within a project and partition (in case id is not provided). Otherwise, the module cannot figure out if the machine was already created or not. |
| `networks` | str | no |  |  | The networks of the machine. IP acquisition mode can be specified by adding :auto or :noauto to the network name. |
| `partition` | str | no |  |  | The partition of the machine. |
| `project` | str | yes |  |  | The project of the machine. |
| `size` | str | no |  |  | The size of the machine. |
| `state` | str | no | `present` | `absent`, `present` | Assert the state of the machine. Use `present` to create or update a machine and `absent` to release it. |
| `tags` | str | no |  |  | The tags of the machine. |
| `userdata` | str | no |  |  | The userdata to inject into the machine provisioning sequence. |



## Return Values

| Key | Type | Returned | Description | Sample |
|-----|------|----------|-------------|--------|
| `id` | str | always | machine id | 306bc4ad-33cd-4744-8c6a-6b601f7179ea |




**Version added:** 2.8


## Examples

```yaml
- name: allocate a machine
  metal_machine:
    name: my-machine
    description: "my machine"
    hostname: my-machine
    networks:
    - internet
    - 5d30b3af-cb2a-4aa3-84e8-52dbf94a326b
    size: c1-xlarge-x86
    partition: fra-equ01
    project: 9ec6882a-cd94-42a7-b667-ffaed43557c7

- name: release a machine
  metal_machine:
    id: 306bc4ad-33cd-4744-8c6a-6b601f7179ea
    state: absent
```


## Authors

- metal-stack



*status: stableinterface, supported_by: community*
