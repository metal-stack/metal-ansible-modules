# Metal Ansible Modules

This repository contains modules and plugins for metal-stack.

The modules use [metal-python](https://github.com/metal-stack/metal-python) for accessing the metal-api. Please make sure you use the correct version of this repository in order to be compatible with the API.

## Modules

| Module Name                                 | Description                           | Requirements |
| ------------------------------------------- | ------------------------------------- | ------------ |
| [metal_ip](library/metal_ip.py)             | Manages metal-stack IP entities       | metal-python |
| [metal_firewall](library/metal_firewall.py) | Manages metal-stack firewall entities | metal-python |
| [metal_machine](library/metal_machine.py)   | Manages metal-stack machine entities  | metal-python |
| [metal_network](library/metal_network.py)   | Manages metal-stack network entities  | metal-python |
| [metal_project](library/metal_project.py)   | Manages metal-stack project entities  | metal-python |

## Dynamic Inventories

| Inventory Name                  | Description                       |
| ------------------------------- | --------------------------------- |
| [metal.py](inventory/metal.py)  | Dynamic inventory for metal-stack |

## Lookup Plugins

| Inventory Name                       | Description         |
| ------------------------------------ | ------------------- |
| [metal](lookup_plugins/metal.py)     | Query the metal-api |

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
