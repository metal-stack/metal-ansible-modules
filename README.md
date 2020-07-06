# Ansible Common

This repository contains modules and plugins for metal-stack.

The modules use [metal-python](https://github.com/metal-stack/metal-python) for accessing the metal-api. Please make sure you use the correct version of this repository in order to be compatible with the API.

## Modules

| Module Name                               | Description                                                  | Requirements      |
| ----------------------------------------- | ------------------------------------------------------------ | ----------------- |
| [metal_ip](library/metal_ip.py)           | Manages metal-stack IP entities                              | metal-python      |
| [metal_network](library/metal_network.py) | Manages metal-stack network entities                         | metal-python      |

## Dynamic Inventories

| Inventory Name               | Description                                          |
| ---------------------------- | ---------------------------------------------------- |
| [Metal](inventory/metal)     | Dynamic inventory from metal-stack                   |

## Usage

It's convenient to use ansible-galaxy in order to use this project. For your project, set up a `requirements.yml`:

```yaml
- src: https://github.com/metal-stack/metal-ansible-modules.git
  name: metal-modules
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
    - name: ansible-common/roles/helm-chart
      vars:
        ...
```
