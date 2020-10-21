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

ANSIBLE_CI_MANAGED_KEY = "ci.metal-stack.io/manager"
ANSIBLE_CI_MANAGED_VALUE = "ansible"
ANSIBLE_CI_MANAGED_TAG = ANSIBLE_CI_MANAGED_KEY + "=" + ANSIBLE_CI_MANAGED_VALUE


class Configuration:
    CONFIG_PATH = os.environ.get("METAL_ANSIBLE_INVENTORY_CONFIG",
                                 os.path.join(os.path.dirname(__file__), "metal_config.yaml"))

    def __init__(self):
        self._config = dict()
        if os.path.isfile(Configuration.CONFIG_PATH):
            with open(Configuration.CONFIG_PATH, "r") as f:
                self._config = yaml.safe_load(f)

    def url(self):
        return self._config.get("url", os.environ.get("METAL_ANSIBLE_INVENTORY_URL", os.environ.get("METALCTL_URL")))

    def token(self):
        return self._config.get("token", os.environ.get("METAL_ANSIBLE_INVENTORY_TOKEN"))

    def hmac(self):
        return self._config.get("hmac", os.environ.get("METAL_ANSIBLE_INVENTORY_HMAC", os.environ.get("METALCTL_HMAC")))

    def hmac_user(self):
        return self._config.get("hmac_user", "Metal-Edit")

    def external_network_id(self):
        return self._config.get("external_network_id", "internet")

    def scope_filters(self):
        return self._config.get("scope_filters", [])

    def static_machine_ip_mapping(self):
        return self._config.get("static_machine_ip_mapping", dict())


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
    c = Configuration()

    d = Driver(url=c.url(), bearer=c.token(), hmac_key=c.hmac(), hmac_user=c.hmac_user())

    request = models.V1MachineFindRequest()
    for scope_filter in c.scope_filters():
        request.__setattr__(scope_filter["name"], scope_filter["value"])

    machines = MachineApi(api_client=d.client).find_machines(request)
    projects = ProjectApi(api_client=d.client).list_projects()

    machine_meta = dict()
    inventory = {"_meta": dict(hostvars=machine_meta)}

    project_map = dict()
    for project in projects:
        project_map[project.meta.id] = project

    static_machine_ip_mapping = c.static_machine_ip_mapping()

    for machine in machines:
        if ANSIBLE_CI_MANAGED_TAG not in machine.tags:
            continue

        if not machine.id or machine.allocation is None:
            continue

        rack_id = machine.rackid
        allocation = machine.allocation
        size_id = machine.size.id if machine.size else None
        partition_id = machine.partition.id if machine.partition else None
        tags = machine.tags

        description = allocation.description
        networks = allocation.networks
        console_password = allocation.console_password
        name = allocation.name
        hostname = allocation.hostname
        project_id = allocation.project
        tenant_id = project_map.get(project_id).tenant_id

        machine_event_log = []
        if machine.events and machine.events.log:
            for e in machine.events.log:
                machine_event_log.append(dict(
                    event=e.event,
                    message=e.message,
                    time=str(e.time),
                ))

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
            is_external = True if c.external_network_id() in network.networkid else False
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

        image = allocation.image
        image_id = None
        image_expiration_date = None
        if image:
            image_id = image.id
            image_expiration_date = str(image.expiration_date)
            # TODO: Can be replaced when we have https://github.com/metal-stack/metal-api/issues/24
            if "firewall" in image.features:
                if len(networks) > 1:
                    is_firewall = True
            if "machine" in image.features:
                is_machine = True

        machine_meta[hostname] = dict(
            ansible_host=ansible_host,
            ansible_user="metal",
            metal_allocated_at=str(allocation.created),
            metal_id=machine.id,
            metal_name=name,
            metal_event_log=machine_event_log,
            metal_hostname=hostname,
            metal_description=description,
            metal_rack_id=rack_id,
            metal_partition=partition_id,
            metal_project=project_id,
            metal_size=size_id,
            metal_image=image_id,
            metal_image_expiration=image_expiration_date,
            metal_console_password=console_password,
            metal_tenant=tenant_id,
            metal_is_firewall=is_firewall,
            metal_is_machine=is_machine,
            metal_internal_ip=internal_ip,
            metal_tags=tags,
        )

        if is_machine:
            _append_to_inventory(inventory, project_id, hostname)
            _append_to_inventory(inventory, size_id, hostname)
            _append_to_inventory(inventory, partition_id, hostname)
            _append_to_inventory(inventory, image_id, hostname)
            _append_to_inventory(inventory, rack_id, hostname)
            _append_to_inventory(inventory, "metal", hostname)
        else:
            _append_to_inventory(inventory, "metal-firewalls", hostname)

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
