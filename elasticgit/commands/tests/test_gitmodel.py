from uuid import uuid4
from elasticgit.commands.gitmodel import MigrateGitModelRepo
from elasticgit.tests.base import ToolBaseTest


class TestMigrateGitModelRepo(ToolBaseTest):

    def setUp(self):
        self.local_workspace = self.mk_workspace(
            name='%s_local' % (self.id(),), auto_destroy=self.destroy)
        self.local_workspace.setup('Test Kees', 'kees@example.org')

        self.remote_workspace = self.mk_workspace(
            name='%s_remote' % (self.id(),), auto_destroy=self.destroy)
        self.remote_workspace.setup('Test Kees', 'kees@example.org')

    def mk_gitmodel_category_data(self, workspace):
        uuid = uuid4().hex
        workspace.sm.store_data(
            'gitcategorymodel/4b65e0c3d5d54107b038e0d1c2305f2b/data.json',
            """{
                "fields": {
                    "subtitle": "",
                    "language": "eng_UK",
                    "title": "Life Tips",
                    "slug": "life-tips",
                    "source": null,
                    "position": 1,
                    "featured_in_navbar": true,
                    "id": "%s"
                },
                "model": "GitCategoryModel"
            }""" % (uuid,), 'Test Category')
        return uuid

    def mk_gitmodel_page_data(self, workspace):
        uuid = uuid4().hex
        workspace.sm.store_data(
            'gitpagemodel/%s/data.json' % (uuid,),
            """{
                "fields": {
                    "subtitle": "",
                    "description": "another test ",
                    "language": "eng_UK",
                    "title": "another test ",
                    "primary_category": "9260e5f7c6ac4540bf4dc80c8e5913c0",
                    "created_at": "2014-10-01T09:11:42+00:00",
                    "featured_in_category": true,
                    "modified_at": "2014-10-12T10:59:24.096582+00:00",
                    "linked_pages": [
                        "eed8150cd2b54621a5b43063595c0e6e",
                        "aa75cea2888d43dd908d4c28b8661d21"
                    ],
                    "slug": "another-test",
                    "content": "<p>Lorem Ipsum is simply dummy text </p>",
                    "source": null,
                    "featured": false,
                    "published": true,
                    "position": 3,
                    "id": "%s"
                },
                "model": "GitPageModel"
            }""" % (uuid,), 'Test Page')
        return uuid

    def test_setup_remotes(self):
        self.mk_gitmodel_category_data(self.remote_workspace)
        self.mk_gitmodel_page_data(self.remote_workspace)
        migrator = MigrateGitModelRepo()
        migrator.run(
            self.remote_workspace.repo.working_dir,
            self.local_workspace.repo.working_dir)
