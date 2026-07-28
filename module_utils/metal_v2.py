import os
import re
import traceback
from abc import ABC, abstractmethod
from datetime import timedelta

from ansible.module_utils.basic import missing_required_lib

try:
    from metalstack.client import client as apiclient

    METAL_STACK_API_AVAILABLE = True
except:
    METAL_STACK_API_AVAILABLE = False
    METAL_STACK_API_IMP_ERR = traceback.format_exc()


class BaseMetalV2Resource(ABC):
    V2_ANSIBLE_CI_MANAGED_KEY = "ci.metal-stack.io/manager"
    V2_ANSIBLE_CI_MANAGED_VALUE = "ansible"
    V2_ANSIBLE_CI_IDENTIFIER_KEY = "ci.metal-stack.io/id"

    V2_AUTH_SPEC = dict(
        api_url=dict(type='str', required=False),
        api_token=dict(type='str', required=False, no_log=True),
        api_timeout=dict(type='int', required=False),
    )

    V2_COMMON_ARG_SPEC = dict(
        identifier=dict(type='str', required=True),
        use_latest_identifier=dict(type='bool', default=False),
        labels=dict(type='dict', required=False),
        state=dict(type='str', choices=[
                   'present', 'absent'], default='present'),
    )

    def __init__(self, module):
        if not METAL_STACK_API_AVAILABLE:
            module.fail_json(
                msg=missing_required_lib("metal-stack-api"),
                exception=METAL_STACK_API_IMP_ERR,
            )

        self._module = module
        self.changed = False
        self._identifier = module.params.get('identifier')
        self._use_latest_identifier = module.params.get(
            'use_latest_identifier')
        self._labels = module.params.get('labels')
        self._state = module.params.get('state')

        client = self._init_client(module)
        self._client: apiclient.Client = client[0]
        self._headers: dict = client[1]

    def _init_client(self, module):
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

    def _get_latest_resource(self, resources):
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
                msg=f"the identifier label {self.V2_ANSIBLE_CI_IDENTIFIER_KEY}={self._identifier} does not return a unique resource. the module cannot figure out on which resource it is supposed to act on.")
            return

        return resources[0]

    @classmethod
    def _create_argument_spec(cls, module_arg_spec):
        argument_spec = cls.V2_AUTH_SPEC.copy()
        argument_spec.update(cls.V2_COMMON_ARG_SPEC)
        argument_spec.update(module_arg_spec)
        return argument_spec

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
            self.V2_ANSIBLE_CI_IDENTIFIER_KEY: self._identifier,
            self.V2_ANSIBLE_CI_MANAGED_KEY: self.V2_ANSIBLE_CI_MANAGED_VALUE,
        }
        return labels

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
