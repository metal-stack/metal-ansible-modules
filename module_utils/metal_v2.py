import os
import re
from abc import ABC, abstractmethod
from datetime import timedelta

from ansible.module_utils.basic import AnsibleModule

try:
    from metalstack.client import client as apiclient

    METAL_STACK_API_AVAILABLE = True
except ImportError:
    METAL_STACK_API_AVAILABLE = False


V2_AUTH_SPEC = dict(
    api_url=dict(type='str', required=False),
    api_token=dict(type='str', required=False, no_log=True),
)

V2_ANSIBLE_CI_MANAGED_KEY = "ci.metal-stack.io/manager"
V2_ANSIBLE_CI_MANAGED_VALUE = "ansible"
V2_ANSIBLE_CI_IDENTIFIER_KEY = "ci.metal-stack.io/id"


def init_client_for_module(module):
    if not METAL_STACK_API_AVAILABLE:
        module.fail_json(msg="metal-stack-api must be installed")

    url = module.params.get("api_url", None)
    if not url:
        url = os.environ.get("METAL_APIV2_URL")
    if not url:
        raise Exception("api_url or METAL_APIV2_URL must be provided")

    token = module.params.get("api_token", None)
    if not token:
        token = os.environ.get("METAL_APIV2_TOKEN")
    if not token:
        raise Exception("api_token or METAL_APIV2_TOKEN must be provided")

    timeout = module.params.get("api_timeout", None)

    args = dict(
        baseurl=url,
    )
    if timeout:
        args["timeout"] = timeout

    return apiclient.Client(**args), dict(Authorization="Bearer " + token)


# taken from this gist: https://gist.github.com/santiagobasulto/698f0ff660968200f873a2f9d1c4113c

TIMEDELTA_REGEX = (r'((?P<days>\d+)d)?'
                   r'((?P<hours>\d+)h)?'
                   r'((?P<minutes>\d+)m)?')
TIMEDELTA_PATTERN = re.compile(TIMEDELTA_REGEX, re.IGNORECASE)


def parse_delta(delta) -> timedelta:
    """ Parses a human readable timedelta (3d5h19m) into a datetime.timedelta.
    Delta includes:
    * Xd days
    * Xh hours
    * Xm minutes
    """
    match = TIMEDELTA_PATTERN.match(delta)
    if match:
        parts = {k: int(v) for k, v in match.groupdict().items() if v}
        return timedelta(**parts)
    else:
        raise RuntimeError(
            "unable to parse timedelta (may only contain minutes, hours and days), valid args look like 8h, 20d4h3m, ...")


def get_latest_resource(self, resources):
    if not resources:
        return None

    if self._use_latest_identifier:
        latest_created = None

        for resource in resources:
            if latest_created is None:
                latest_created = resource
                continue

            if resource.meta.created_at.ToDatetime() > latest_created.meta.created_at.ToDatetime():
                latest_created = resource

        return latest_created

    if len(resources) != 1:
        self._module.fail_json(
            msg=f"the identifier label {V2_ANSIBLE_CI_IDENTIFIER_KEY}={self._identifier} does not return a unique resource. the module cannot figure out on which resource it is supposed to act on.")
        return

    return resources[0]


COMMON_ARG_SPEC = dict(
    identifier=dict(type='str', required=True),
    use_latest_identifier=dict(type='bool', default=False),
    labels=dict(type='dict', required=False),
    state=dict(type='str', choices=['present', 'absent'], default='present'),
)


class BaseMetalV2Resource(ABC):
    def __init__(self, module, module_arg_spec=None):
        if not METAL_STACK_API_AVAILABLE:
            raise RuntimeError("metal-stack-api must be installed")

        self._module = module
        self.changed = False
        self._identifier = module.params.get('identifier')
        self._use_latest_identifier = module.params.get('use_latest_identifier')
        self._labels = module.params.get('labels')
        self._state = module.params.get('state')
        client = init_client_for_module(module)
        self._client: apiclient.Client = client[0]
        self._headers: dict = client[1]

    @classmethod
    def _create_argument_spec(cls, module_arg_spec):
        argument_spec = V2_AUTH_SPEC.copy()
        argument_spec.update(COMMON_ARG_SPEC)
        argument_spec.update(module_arg_spec)
        return argument_spec

    @classmethod
    def create_module(cls, module_arg_spec, **kwargs):
        argument_spec = cls._create_argument_spec(module_arg_spec)
        return AnsibleModule(
            argument_spec=argument_spec,
            supports_check_mode=True,
            **kwargs,
        )

    @classmethod
    def run_module(cls, module_arg_spec, **kwargs):
        module = cls.create_module(module_arg_spec, **kwargs)
        instance = cls(module)
        instance.run()

        result = instance._result()
        module.exit_json(**result)

    @abstractmethod
    def _get_resource(self):
        pass

    def run(self):
        if self._module.check_mode:
            return

        self._find()

        if self._state == "present":
            if self._get_resource():
                self._update()
                return

            self._create()
            self.changed = True

        elif self._state == "absent":
            if self._get_resource():
                self._delete()
                self.changed = True

    def _build_labels(self):
        labels = self._labels if self._labels else dict()
        labels = labels | {
            V2_ANSIBLE_CI_IDENTIFIER_KEY: self._identifier,
            V2_ANSIBLE_CI_MANAGED_KEY: V2_ANSIBLE_CI_MANAGED_VALUE,
        }
        return labels

    def _handle_connect_error(self, e):
        self._module.fail_json(
            msg="request to metal-apiserver failed", error=str(e))

    @abstractmethod
    def _find(self):
        pass

    @abstractmethod
    def _create(self):
        pass

    @abstractmethod
    def _update(self):
        pass

    @abstractmethod
    def _delete(self):
        pass

    @abstractmethod
    def _result(self):
        pass
