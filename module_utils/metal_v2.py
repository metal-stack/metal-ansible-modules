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


def init_client_for_module(module):
    if not METAL_STACK_API_AVAILABLE:
        module.fail_json(msg="metal-stack-api must be installed")

    url = module.params.get("api_url", os.environ.get("METALCTLV2_API_URL"))
    token = module.params.get(
        "api_token", os.environ.get("METALCTLV2_API_TOKEN"))
    timeout = module.params.get("api_timeout", None)

    args = dict(
        baseurl=url,
        token=token
    )

    if timeout:
        args["timeout"] = timeout

    return apiclient.Client(**args)
