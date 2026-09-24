# metal

Query the metal-api

## Synopsis

- Looks up API entities in the metal-api.

- Requires Python 3.


## Requirements

- [metal-python](https://pypi.org/project/metal-python/)


## Parameters

| Parameter | Type | Required | Default | Choices | Comments |
|-----------|------|----------|---------|---------|----------|
| `_terms` | str | no |  |  | First term can be set to 'get' or 'search', second one to the desired entity If set, request and entity can be omitted |
| `entity` | str | yes |  |  | the entity to lookup |
| `query` | str | no |  |  | Arbitrary query parameters passed on to the get request or request search body It can be that certain query parameters overlap with the Ansible lookup plugin constructor (e.g. 'name'). If this happens, you can prefix your parameter with an underscore, which will be removed before the request. |
| `request` | str | no | `get` |  | The type of the request (get or search). 'get' returns a single result and needs the primary key to be added as the query term 'search' returns a list of results filtered by the given query params |



## Return Values

*No return values.*


**Version added:** 2.9


## Examples

```yaml
- name: Fetch a list of partition
  set_fact:
    projects: "{{ lookup('metal', request='search', entity='partition') }}"
```


## Authors

- metal-stack



*status: stableinterface, supported_by: community*
