import os

try:
    from metal_python.driver import Driver

    METAL_PYTHON_AVAILABLE = True
except ImportError:
    METAL_PYTHON_AVAILABLE = False

AUTH_SPEC = dict(
    api_url=dict(type='str', required=False),
    api_hmac=dict(type='str', required=False, no_log=True),
    api_token=dict(type='str', required=False, no_log=True),
)


def init_driver_for_module(module):
    if not METAL_PYTHON_AVAILABLE:
        module.fail_json(msg="metal_python must be installed")

    url = module.params.get("api_url", os.environ.get("METALCTL_URL"))
    hmac = module.params.get("api_hmac", os.environ.get("METALCTL_HMAC"))
    token = module.params.get("api_token", os.environ.get("METALCTL_APITOKEN"))

    return init_driver(url, hmac, token)


def init_driver(url, hmac, token):
    return Driver(url, token, hmac)
