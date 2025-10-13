import os

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
