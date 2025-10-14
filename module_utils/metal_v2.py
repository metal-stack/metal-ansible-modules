import os
import re
from datetime import timedelta

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


def init_client_for_module(module) -> apiclient.Client:
    if not METAL_STACK_API_AVAILABLE:
        module.fail_json(msg="metal-stack-api must be installed")

    url = module.params.get("api_url", None)
    if not url:
        url = os.environ.get("METALCTLV2_API_URL")
    if not url:
        raise Exception("api_url or METALCTLV2_API_URL must be provided")

    token = module.params.get("api_token", None)
    if not token:
        token = os.environ.get("METALCTLV2_API_TOKEN")
    if not token:
        raise Exception("api_token or METALCTLV2_API_TOKEN must be provided")

    timeout = module.params.get("api_timeout", None)

    args = dict(
        baseurl=url,
        token=token
    )

    if timeout:
        args["timeout"] = timeout

    return apiclient.Client(**args)


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
