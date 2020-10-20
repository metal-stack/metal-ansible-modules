#!/usr/bin/env python

import argparse
import os
import json
import yaml

try:
    from metal_python.driver import Driver
    from metal_python.api import MachineApi, ProjectApi
    from metal_python import models

    METAL_PYTHON_AVAILABLE = True
except ImportError:
    METAL_PYTHON_AVAILABLE = False

CONFIG_PATH = os.environ.get("METAL_ANSIBLE_INVENTORY_CONFIG",
                             os.path.join(os.path.dirname(__file__), "metal_config.yaml"))

CONFIG = dict()
if os.path.isfile(CONFIG_PATH):
    with open(CONFIG_PATH, "r") as f:
        CONFIG = yaml.safe_load(f)

URL = os.environ.get("METAL_ANSIBLE_INVENTORY_URL", CONFIG.get("url"))
TOKEN = os.environ.get("METAL_ANSIBLE_INVENTORY_TOKEN", CONFIG.get("token"))
HMAC = os.environ.get("METAL_ANSIBLE_INVENTORY_HMAC", CONFIG.get("hmac"))

ANSIBLE_CI_MANAGED_KEY = "ci.metal-stack.io/manager"
ANSIBLE_CI_MANAGED_VALUE = "ansible"
ANSIBLE_CI_MANAGED_TAG = ANSIBLE_CI_MANAGED_KEY + "=" + ANSIBLE_CI_MANAGED_VALUE


def run():
    if not METAL_PYTHON_AVAILABLE:
        # this allows to install metal_python during playbook execution, just refresh the inventory
        # after installation
        return return_json(dict())

    args = parse_arguments()
    if args.host:
        result = host_vars(args.host)
    else:
        result = host_list()

    return_json(result)


def parse_arguments():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument(
        "--list",
        action="store_true",
        help="lists groups and hosts"
    )
    group.add_argument(
        "--host",
        help="returns host variables of the dynamic inventory source"
    )
    return parser.parse_args()


def host_list():
    d = Driver(url=URL, bearer=TOKEN, hmac_key=HMAC)

    request = models.V1MachineFindRequest()
    scope_filters = CONFIG.get("scope_filters", [])
    for scope_filter in scope_filters:
        request.__setattr__(scope_filter["name"], scope_filter["value"])

    machines = MachineApi(api_client=d.client).find_machines(request)
    projects = ProjectApi(api_client=d.client).list_projects()

    machine_meta = dict()
    inventory = {"_meta": dict(hostvars=machine_meta)}

    static_machine_ip_mapping = CONFIG.get("static_machine_ip_mapping", dict())

    project_map = dict()
    for project in projects:
        project_map[project.meta.id] = project

    for machine in machines:
        id = machine.id
        description = machine.description
        rack_id = machine.rackid
        allocation = machine.allocation
        size_id = machine.size.id if machine.size else None
        partition_id = machine.partition.id if machine.partition else None
        tags = machine.tags

        if ANSIBLE_CI_MANAGED_TAG not in tags:
            continue

        if allocation is None or not id:
            continue

        networks = allocation.networks
        console_password = allocation.console_password
        name = allocation.name
        hostname = allocation.hostname
        project_id = allocation.project
        tenant_id = project_map.get(project_id).tenant_id
        image = allocation.image
        image_id = None
        if image:
            image_id = image.id

        internal_ip = None
        for network in networks:
            if network.private:
                internal_ips = network.ips
                if len(internal_ips) > 0:
                    internal_ip = internal_ips[0]
                    break

        # TODO: It is somehow hard to determine the IP of the machine to connect with from the internet...
        external_ip = None
        for network in networks:
            is_external = True if "internet" in network.networkid else False
            if is_external:
                external_ips = network.ips
                if len(external_ips) > 0:
                    external_ip = external_ips[0]
                    break

        ansible_host = allocation.hostname if allocation.hostname != "" else name
        ansible_host = external_ip if external_ip is not None else ansible_host
        if not ansible_host:
            # if there is no name, no host name and no external ip... we skip this host
            continue

        is_machine = False
        is_firewall = False

        # TODO: Can be replaced when we have https://github.com/metal-stack/metal-api/issues/24
        if image:
            image_features = image.features

            if "firewall" in image_features:
                if len(networks) > 1:
                    is_firewall = True
            if "machine" in image_features:
                is_machine = True

        machine_meta[hostname] = dict(
            ansible_host=ansible_host,
            metal_id=id,
            metal_name=name,
            metal_hostname=hostname,
            metal_description=description,
            metal_rack_id=rack_id,
            metal_project_id=project_id,
            metal_console_password=console_password,
            metal_tenant_id=tenant_id,
            metal_is_firewall=is_firewall,
            metal_is_machine=is_machine,
            metal_tags=tags,
        )

        if is_machine:
            _append_to_inventory(inventory, project_id, hostname)
            _append_to_inventory(inventory, size_id, hostname)
            _append_to_inventory(inventory, partition_id, hostname)
            _append_to_inventory(inventory, image_id, hostname)
            _append_to_inventory(inventory, "metal", hostname)
        else:
            _append_to_inventory(inventory, "metal-firewalls", hostname)

        if internal_ip:
            machine_meta[hostname]["metal_internal_ip"] = internal_ip
        if size_id:
            machine_meta[hostname]["metal_size_id"] = size_id
        if partition_id:
            machine_meta[hostname]["metal_partition_id"] = partition_id
        if image_id:
            machine_meta[hostname]["metal_image_id"] = image_id

        if hostname in static_machine_ip_mapping:
            machine_meta[hostname]["ansible_host"] = static_machine_ip_mapping[hostname]

    return inventory


def _append_to_inventory(inventory, key, host):
    if not key:
        return

    if key not in inventory:
        inventory[key] = []

    hosts = inventory[key]
    hosts.append(host)


def host_vars(host):
    # currently not required because host list returns _meta information
    return dict()


def return_json(result):
    print(json.dumps(result, sort_keys=True, indent=4))


if __name__ == '__main__':
    run()
