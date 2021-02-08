#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
from abc import ABC, abstractmethod

try:
    import metal_python.api as apis
    from metal_python import models
    from metal_python.driver import Driver

    METAL_PYTHON_AVAILABLE = True
except ImportError:
    METAL_PYTHON_AVAILABLE = False

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

DOCUMENTATION = """
    lookup: metal
    author: metal-stack
    version_added: '2.9'
    short_description: Query the metal-api
    description:
      - Looks up API entities in the metal-api.
      - Requires Python 3.
    options:
      request:
        description: 
        - The type of the request (get or search).
        - "'get' returns a single result and needs the primary key to be added as the query term"
        - "'search' returns a list of results filtered by the given query params"
        default: get
      entity:
        description: the entity to lookup
        required: True
      _terms:
         description: 
         - First term can be set to 'get' or 'search', second one to the desired entity
         - If set, request and entity can be omitted
         required: False
      query:
        description: 
          - Arbitrary query parameters passed on to the get request or request search body 
          - It can be that certain query parameters overlap with the Ansible lookup plugin constructor (e.g. 'name').
          - If this happens, you can prefix your parameter with an underscore, which will be removed before the request.
        required: False
    requirements:
      - "metal-python >= 0.9.0"
    notes:
      - Uses the metal-python client for accessing the API. (https://github.com/metal-stack/metal-python)
"""

EXAMPLES = """
- name: Fetch a list of partition
  set_fact:
    projects: "{{ lookup('metal', request='search', entity='partition') }}"
"""


class Requester(ABC):
    @abstractmethod
    def __init__(self, _):
        pass

    @abstractmethod
    def get(self, **kwargs):
        pass

    @abstractmethod
    def search(self, **kwargs):
        pass


class PartitionRequester(Requester):
    def __init__(self, client):
        super().__init__(client)
        self.api = apis.PartitionApi(api_client=client)

    def get(self, **kwargs):
        if "id" not in kwargs:
            raise AnsibleError("id must be present")
        return self.api.find_partition(id=kwargs.get("id"))

    def search(self, **kwargs):
        return self.api.list_partitions()


class SizeRequester(Requester):
    def __init__(self, client):
        super().__init__(client)
        self.api = apis.SizeApi(api_client=client)

    def get(self, **kwargs):
        if "id" not in kwargs:
            raise AnsibleError("id must be present")
        return self.api.find_size(id=kwargs.get("id"))

    def search(self, **kwargs):
        return self.api.list_sizes()


class MachineRequester(Requester):
    def __init__(self, client):
        super().__init__(client)
        self.api = apis.MachineApi(api_client=client)

    def get(self, **kwargs):
        if "id" not in kwargs:
            raise AnsibleError("id must be present")
        return self.api.find_machine(id=kwargs.get("id"))

    def search(self, **kwargs):
        body = models.V1MachineFindRequest(**kwargs)
        return self.api.find_machines(body)


class NetworkRequester(Requester):
    def __init__(self, client):
        super().__init__(client)
        self.api = apis.NetworkApi(api_client=client)

    def get(self, **kwargs):
        if "id" not in kwargs:
            raise AnsibleError("id must be present")
        return self.api.find_network(id=kwargs.get("id"))

    def search(self, **kwargs):
        body = models.V1NetworkFindRequest(**kwargs)
        return self.api.find_networks(body)


class IPRequester(Requester):
    def __init__(self, client):
        super().__init__(client)
        self.api = apis.IpApi(api_client=client)

    def get(self, **kwargs):
        if "id" not in kwargs:
            raise AnsibleError("id must be present")
        return self.api.find_ip(id=kwargs.get("id"))

    def search(self, **kwargs):
        body = models.V1IPFindRequest(**kwargs)
        return self.api.find_i_ps(body)


class FirewallRequester(Requester):
    def __init__(self, client):
        super().__init__(client)
        self.api = apis.FirewallApi(api_client=client)

    def get(self, **kwargs):
        if "id" not in kwargs:
            raise AnsibleError("id must be present")
        return self.api.find_firewall(id=kwargs.get("id"))

    def search(self, **kwargs):
        body = models.V1FirewallFindRequest(**kwargs)
        return self.api.find_firewalls(body)


class ImageRequester(Requester):
    def __init__(self, client):
        super().__init__(client)
        self.api = apis.ImageApi(api_client=client)

    def get(self, **kwargs):
        if "id" not in kwargs:
            raise AnsibleError("id must be present")
        return self.api.find_image(id=kwargs.get("id"))

    def search(self, **kwargs):
        return self.api.list_images()


class ProjectRequester(Requester):
    def __init__(self, client):
        super().__init__(client)
        self.api = apis.ProjectApi(api_client=client)

    def get(self, **kwargs):
        if "id" not in kwargs:
            raise AnsibleError("id must be present")
        return self.api.find_project(id=kwargs.get("id"))

    def search(self, **kwargs):
        body = models.V1ProjectFindRequest(**kwargs)
        return self.api.find_projects(body)


class SwitchRequester(Requester):
    def __init__(self, client):
        super().__init__(client)
        self.api = apis.SwitchApi(api_client=client)

    def get(self, **kwargs):
        if "id" not in kwargs:
            raise AnsibleError("id must be present")
        return self.api.find_switch(id=kwargs.get("id"))

    def search(self, **kwargs):
        return self.api.list_switches()


class LookupModule(LookupBase):
    _entities = dict(
        image=ImageRequester,
        ip=IPRequester,
        firewall=FirewallRequester,
        machine=MachineRequester,
        network=NetworkRequester,
        partition=PartitionRequester,
        project=ProjectRequester,
        size=SizeRequester,
        switch=SwitchRequester,
    )
    _request_types = ["get", "search"]

    def run(self, terms, variables=None, **kwargs):
        if not METAL_PYTHON_AVAILABLE:
            raise RuntimeError("metal_python must be installed")

        url = kwargs.pop("api_url", variables.get("metal_api_url", os.environ.get("METALCTL_URL")))
        hmac = kwargs.pop("api_hmac", variables.get("metal_api_hmac", os.environ.get("METALCTL_HMAC")))
        hmac_user = kwargs.pop("api_hmac_user", variables.get("metal_api_hmac_user", "Metal-Edit"))
        token = kwargs.pop("api_token", variables.get("metal_api_token", os.environ.get("METALCTL_APITOKEN")))

        entity = kwargs.pop("entity", terms[1] if len(terms) == 2 else None)
        if not entity:
            raise AnsibleError("entity must be present and one of %s" % LookupModule._entities.keys())

        request = kwargs.pop("request", terms[0] if len(terms) == 2 else "get")
        if request not in LookupModule._request_types:
            raise AnsibleError("request must be present and one of %s" % LookupModule._request_types)

        # some query parameters overlap with default Ansible lookup plugin input params
        # allow a user to use a query param by prepending an underscore
        query = dict()
        for k, v in kwargs.items():
            if len(k) > 1 and k.startswith("_"):
                query[k[1:]] = v
            else:
                query[k] = v

        d = Driver(url, token, hmac, hmac_user=hmac_user)

        requester = LookupModule._entities[entity](client=d.client)

        if request == "get":
            return [requester.get(**query).to_dict()]

        result = list()
        for e in requester.search(**query):
            result.append(e.to_dict())
        return [result]
