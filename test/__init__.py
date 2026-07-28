import mock
import os
import json
import unittest

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes

from module_utils import metal

MODULES_PATH = os.path.join(os.path.dirname(
    os.path.abspath(os.path.dirname(__file__))), 'library')
MODULE_UTILS_PATH = os.path.join(os.path.dirname(
    os.path.abspath(os.path.dirname(__file__))), 'module_utils')
INVENTORY_PATH = os.path.join(os.path.dirname(
    os.path.abspath(os.path.dirname(__file__))), 'inventory')

V2_TEST_COMMON_LABELS = {
    "ci.metal-stack.io/id": "test",
    "ci.metal-stack.io/manager": "ansible",
}

V2_TEST_API_URL = "http://test"
V2_TEST_API_TOKEN = "token"


def set_module_args(args):
    """prepare arguments so that they will be picked up during module creation"""
    args = json.dumps({'ANSIBLE_MODULE_ARGS': args})
    basic._ANSIBLE_ARGS = to_bytes(args)
    basic._ANSIBLE_PROFILE = 'legacy'


class AnsibleExitJson(Exception):
    """Exception class to be raised by module.exit_json and caught by the test case"""

    def __init__(self, kwargs):
        self.module_results = kwargs
        super(AnsibleExitJson, self).__init__(kwargs)


class AnsibleFailJson(Exception):
    """Exception class to be raised by module.fail_json and caught by the test case"""

    def __init__(self, kwargs):
        self.module_results = kwargs
        super(AnsibleFailJson, self).__init__(kwargs)


def exit_json(_, **kwargs):
    """function to patch over exit_json; package return data into an exception"""
    if 'changed' not in kwargs:
        kwargs['changed'] = False
    raise AnsibleExitJson(kwargs)


def fail_json(_, **kwargs):
    """function to patch over fail_json; package return data into an exception"""
    kwargs['failed'] = True
    raise AnsibleFailJson(kwargs)


class MetalModules(unittest.TestCase):
    def defaultSetUpTasks(self):
        modules = {
            'ansible.module_utils.metal': metal,
        }
        self.module_patcher = mock.patch.dict('sys.modules', modules)
        self.module_patcher.start()
        self.addCleanup(self.module_patcher.stop)

        self.mock_module_helper = mock.patch.multiple(basic.AnsibleModule,
                                                      exit_json=exit_json,
                                                      fail_json=fail_json)
        self.mock_module_helper.start()
        self.addCleanup(self.mock_module_helper.stop)


class V2MetalModules(MetalModules):
    interceptor = None

    def setUp(self):
        super().defaultSetUpTasks()

        import module_utils.metal_v2 as metal_v2_mod

        self.v2_mod_patcher = mock.patch.dict(
            "sys.modules",
            {"ansible.module_utils.metal_v2": metal_v2_mod},
        )
        self.v2_mod_patcher.start()
        self.addCleanup(self.v2_mod_patcher.stop)

        self._original_init_client = metal_v2_mod.BaseMetalV2Resource._init_client

        self._init_client_patcher = mock.patch.object(
            metal_v2_mod.BaseMetalV2Resource,
            "_init_client",
            side_effect=self._patched_init_client,
        )
        self._init_client_patcher.start()
        self.addCleanup(self._init_client_patcher.stop)

    def _patched_init_client(self, module):
        client, headers = self._original_init_client(object(), module)
        if self.interceptor is not None:
            client._interceptors = [self.interceptor]
        return client, headers

    def tearDown(self):
        if self.interceptor is not None and hasattr(self.interceptor, 'assert_all_calls_used'):
            self.interceptor.assert_all_calls_used()
