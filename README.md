# Metal Ansible Modules

This repository contains modules and plugins for metal-stack.

The modules use [metal-python](https://github.com/metal-stack/metal-python) for accessing the metal-api. Please make sure you use the correct version of this repository in order to be compatible with the API.

The v2 modules require the [metal-stack-api](https://pypi.org/project/metal-stack-api/) python client from the [api](https://github.com/metal-stack/api) repository.

## Modules

| Module Name                                     | Description                           | Requirements |
| ----------------------------------------------- | ------------------------------------- | ------------ |
| [metal_ip](docs/metal_ip.md)                    | Manages metal-stack IP entities       | metal-python |
| [metal_firewall](docs/metal_firewall.md)        | Manages metal-stack firewall entities | metal-python |
| [metal_machine](docs/metal_machine.md)          | Manages metal-stack machine entities  | metal-python |
| [metal_network](docs/metal_network.md)          | Manages metal-stack network entities  | metal-python |
| [metal_project](docs/metal_project.md)          | Manages metal-stack project entities  | metal-python |

## V2 Modules

| Module Name                                         | Description                            | Requirements    |
| --------------------------------------------------- | -------------------------------------- | --------------- |
| [metal_v2_admin_project](docs/metal_v2_admin_project.md) | Manages metal-stack project entities   | metal-stack-api |
| [metal_v2_admin_tenant](docs/metal_v2_admin_tenant.md)   | Manages metal-stack tenant entities    | metal-stack-api |
| [metal_v2_admin_token](docs/metal_v2_admin_token.md)     | Manages metal-stack api token entities | metal-stack-api |
| [metal_v2_api_token](docs/metal_v2_api_token.md)         | Manages metal-stack api token entities | metal-stack-api |
| [metal_v2_project](docs/metal_v2_project.md)             | Manages metal-stack project entities   | metal-stack-api |
| [metal_v2_tenant](docs/metal_v2_tenant.md)               | Manages metal-stack tenant entities    | metal-stack-api |


## Dynamic Inventories

| Inventory Name                              | Description                       |
| ------------------------------------------- | --------------------------------- |
| [metal](docs/inventory_metal.md)            | Dynamic inventory for metal-stack |

## Lookup Plugins

| Plugin Name                              | Description         |
| ---------------------------------------- | ------------------- |
| [metal](docs/lookup_metal.md)            | Query the metal-api |

## Usage

It's convenient to use ansible-galaxy in order to use this project. For your project, set up a `requirements.yml`:

```yaml
- src: https://github.com/metal-stack/metal-ansible-modules.git
  name: metal-ansible-modules
  version: master
```

You can then download the roles with the following command:

```bash
ansible-galaxy install -r requirements.yml
```

Then reference the roles in your playbooks like this:

```yaml
- name: Deploy something
  hosts: localhost
  connection: local
  gather_facts: no
  roles:
    - metal-ansible-modules
```

## Develop

Here is one way how you can execute the modules locally for development:

- Start the [mini-lab](https://github.com/metal-stack/mini-lab)
- In the mini-lab folder set dev-env with `eval $(make dev-env)`
- Switch to this repository folder
- Adjust the proper API version you develop against in the [Dockerfile](./Dockerfile.test)
- Run `run-v2-test-example`
