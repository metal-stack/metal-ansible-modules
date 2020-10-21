import sys
from mock import patch
from test import (
    MetalModules,
    AnsibleFailJson,
    AnsibleExitJson,
    set_module_args,
    MODULES_PATH,
)
from metal_python import models

sys.path.insert(0, MODULES_PATH)


class TestMetalProjectModule(MetalModules):
    def setUp(self):
        self.defaultSetUpTasks()

        import metal_project
        self.module = metal_project

    @patch("metal_python.api.project_api.ProjectApi.find_projects",
           side_effect=[
               []
           ])
    @patch("metal_python.api.project_api.ProjectApi.create_project",
           side_effect=[
               models.V1ProjectResponse(
                   description="desc",
                   meta=models.V1Meta(
                       id="656c784a-77f9-4d8c-9382-4d42d1b14eb0",
                       annotations={
                           "ci.metal-stack.io/manager": "ansible",
                       },
                       labels=[
                           "a-label",
                       ],
                   ),
                   name="project-a",
                   tenant_id="tt")
           ])
    def test_project_present(self, create_mock, find_mock):
        set_module_args(
            dict(
                api_url="http://somewhere",
                api_hmac="hmac",
                name="project-a",
                tenant="tt",
                description="desc",
                labels=["a-label"],
            )
        )

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        find_mock.assert_called()
        find_mock.assert_called_with(
            models.V1ProjectFindRequest(
                name="project-a"
            )
        )
        create_mock.assert_called()
        create_mock.assert_called_with(
            models.V1ProjectCreateRequest(
                description="desc",
                name="project-a",
                tenant_id="tt",
                meta=models.V1Meta(
                    annotations={
                        "ci.metal-stack.io/manager": "ansible",
                    },
                    labels=[
                        "a-label",
                    ],
                ),
            )
        )

        expected = dict(
            id="656c784a-77f9-4d8c-9382-4d42d1b14eb0",
            changed=True,
        )
        self.assertDictEqual(result.exception.module_results, expected)

    @patch("metal_python.api.project_api.ProjectApi.find_projects",
           side_effect=[
               [
                   models.V1ProjectResponse(
                       description="desc",
                       meta=models.V1Meta(
                           id="656c784a-77f9-4d8c-9382-4d42d1b14eb0",
                           annotations={
                               "ci.metal-stack.io/manager": "ansible",
                           },
                           labels=[
                               "a-label",
                           ],
                       ),
                       name="project-a",
                       tenant_id="tt",
                   )
               ]
           ])
    def test_project_present_already_exists(self, find_mock):
        set_module_args(
            dict(
                api_url="http://somewhere",
                api_hmac="hmac",
                name="project-a",
                tenant="tt",
                description="desc",
                labels=["a-label"],
            )
        )

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        find_mock.assert_called()
        find_mock.assert_called_with(
            models.V1ProjectFindRequest(
                name="project-a"
            )
        )

        expected = dict(
            id="656c784a-77f9-4d8c-9382-4d42d1b14eb0",
            changed=False,
        )
        self.assertDictEqual(result.exception.module_results, expected)

    @patch("metal_python.api.project_api.ProjectApi.find_projects",
           side_effect=[
               [
                   models.V1ProjectResponse(
                       description="desc",
                       meta=models.V1Meta(
                           id="656c784a-77f9-4d8c-9382-4d42d1b14eb0",
                           annotations={
                               "ci.metal-stack.io/manager": "ansible",
                           },
                           labels=[
                               "a-label",
                           ],
                       ),
                       name="project-a",
                       tenant_id="tt",
                   )
               ]
           ])
    @patch("metal_python.api.project_api.ProjectApi.update_project",
           side_effect=[
               models.V1ProjectResponse(
                   description="desc",
                   meta=models.V1Meta(
                       id="656c784a-77f9-4d8c-9382-4d42d1b14eb0",
                       annotations={
                           "ci.metal-stack.io/manager": "ansible",
                       },
                       labels=[
                           "a-label",
                       ],
                   ),
                   name="project-a",
                   tenant_id="tt")
           ])
    def test_project_present_update(self, update_mock, find_mock):
        set_module_args(
            dict(
                api_url="http://somewhere",
                api_hmac="hmac",
                name="project-a",
                tenant="new-tenant",
                description="desc",
                labels=["a-label", "second-label"],
            )
        )

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        find_mock.assert_called()
        find_mock.assert_called_with(
            models.V1ProjectFindRequest(
                name="project-a"
            )
        )
        update_mock.assert_called()
        update_mock.assert_called_with(
            models.V1ProjectUpdateRequest(
                tenant_id="new-tenant",
                meta=models.V1Meta(
                    id="656c784a-77f9-4d8c-9382-4d42d1b14eb0",
                    labels=[
                        "a-label",
                        "second-label",
                    ],
                ),
            )
        )

        expected = dict(
            id="656c784a-77f9-4d8c-9382-4d42d1b14eb0",
            changed=True,
        )
        self.assertDictEqual(result.exception.module_results, expected)

    @patch("metal_python.api.project_api.ProjectApi.find_projects",
           side_effect=[
               [
                   models.V1ProjectResponse(
                       description="desc",
                       meta=models.V1Meta(
                           id="656c784a-77f9-4d8c-9382-4d42d1b14eb0",
                           annotations={
                               "ci.metal-stack.io/manager": "ansible",
                           },
                           labels=[
                               "a-label",
                           ],
                       ),
                       name="project-a",
                       tenant_id="tt",
                   )
               ]
           ])
    @patch("metal_python.api.project_api.ProjectApi.delete_project",
           side_effect=[
               models.V1ProjectResponse(
                   description="desc",
                   meta=models.V1Meta(
                       id="656c784a-77f9-4d8c-9382-4d42d1b14eb0",
                       annotations={
                           "ci.metal-stack.io/manager": "ansible",
                       },
                       labels=[
                           "a-label",
                       ],
                   ),
                   name="project-a",
                   tenant_id="tt")
           ])
    def test_project_absent(self, delete_mock, find_mock):
        set_module_args(
            dict(
                api_url="http://somewhere",
                api_hmac="hmac",
                name="project-a",
                tenant="tt",
                description="desc",
                labels=["a-label"],
                state="absent",
            )
        )

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        find_mock.assert_called()
        find_mock.assert_called_with(
            models.V1ProjectFindRequest(
                name="project-a"
            )
        )
        delete_mock.assert_called()
        delete_mock.assert_called_with("656c784a-77f9-4d8c-9382-4d42d1b14eb0")

        expected = dict(
            id="656c784a-77f9-4d8c-9382-4d42d1b14eb0",
            changed=True,
        )
        self.assertDictEqual(result.exception.module_results, expected)
