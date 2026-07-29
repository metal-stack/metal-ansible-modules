# metal_firewall

A module to manage metal firewall entities

## Synopsis

- Manages firewall entities in the metal-api.

- Requires metal_python to be installed.


## Requirements

- [metal-python](https://pypi.org/project/metal-python/)


## Parameters

| Parameter | Type | Required | Default | Choices | Comments |
|-----------|------|----------|---------|---------|----------|
| `description` | str | no |  |  | The description of the firewall. |
| `hostname` | str | no |  |  | The hostname of the firewall. |
| `id` | str | no |  |  | The id of the firewall, user for specific firewall allocation. |
| `image` | str | no |  |  | The image of the firewall. |
| `ips` | str | no |  |  | The ips of the firewall. |
| `name` | str | no |  |  | The name of the firewall, which must be unique within a project and partition (in case id is not provided). Otherwise, the module cannot figure out if the firewall was already created or not. |
| `networks` | str | no |  |  | The networks of the firewall. IP acquisition mode can be specified by adding :auto or :noauto to the network name. |
| `partition` | str | no |  |  | The partition of the firewall. |
| `project` | str | yes |  |  | The project of the firewall. |
| `rules` | str | no |  |  | Firewall rules to be deployed to the firewall during provisioning. By default the firewall drops all traffic from the node's private network. |
| `size` | str | no |  |  | The size of the firewall. |
| `state` | str | no | `present` | `absent`, `present` | Assert the state of the firewall. Use `present` to create or update a firewall and `absent` to release it. |
| `tags` | str | no |  |  | The tags of the firewall. |



## Return Values

| Key | Type | Returned | Description | Sample |
|-----|------|----------|-------------|--------|
| `id` | str | always | firewall id | 306bc4ad-33cd-4744-8c6a-6b601f7179ea |




**Version added:** 2.8


## Examples

```yaml
- name: allocate a firewall
  metal_firewall:
    name: my-firewall
    description: "my firewall"
    hostname: my-firewall
    networks:
    - internet
    - 5d30b3af-cb2a-4aa3-84e8-52dbf94a326b
    size: c1-xlarge-x86
    partition: fra-equ01
    project: 9ec6882a-cd94-42a7-b667-ffaed43557c7
    rules:
      ingress:
        - comment: ssh
          source:
            - 192.168.2.0/24
          ports: [22]
          protocol: tcp
      egress:
        - comment: reach out to internet
          ports: [53,80,123,443]
          to:
            - 0.0.0.0/0

- name: release a firewall
  metal_firewall:
    id: 306bc4ad-33cd-4744-8c6a-6b601f7179ea
    state: absent
```


## Authors

- metal-stack



*status: stableinterface, supported_by: community*
