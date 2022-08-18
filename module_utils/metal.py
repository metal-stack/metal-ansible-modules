import os

try:
    from metal_python.driver import Driver

    METAL_PYTHON_AVAILABLE = True
except ImportError:
    METAL_PYTHON_AVAILABLE = False

AUTH_SPEC = dict(
    api_url=dict(type='str', required=False),
    api_hmac=dict(type='str', required=False, no_log=True),
    api_hmac_user=dict(type='str', required=False, default='Metal-Edit'),
    api_token=dict(type='str', required=False, no_log=True),
)
ANSIBLE_CI_MANAGED_KEY = "ci.metal-stack.io/manager"
ANSIBLE_CI_MANAGED_VALUE = "ansible"
ANSIBLE_CI_MANAGED_TAG = ANSIBLE_CI_MANAGED_KEY + "=" + ANSIBLE_CI_MANAGED_VALUE
ANSIBLE_CI_MANAGED_LABEL = {ANSIBLE_CI_MANAGED_KEY: ANSIBLE_CI_MANAGED_VALUE}


def init_driver_for_module(module):
    if not METAL_PYTHON_AVAILABLE:
        module.fail_json(msg="metal_python must be installed")

    url = module.params.get("api_url", os.environ.get("METALCTL_API_URL"))
    hmac = module.params.get("api_hmac", os.environ.get("METALCTL_HMAC"))
    token = module.params.get("api_token", os.environ.get("METALCTL_APITOKEN"))
    hmac_user = module.params.get("api_hmac_user")

    return init_driver(url, hmac, token, hmac_user)


def init_driver(url, hmac, token, hmac_user):
    return Driver(url, token, hmac, hmac_user=hmac_user)
