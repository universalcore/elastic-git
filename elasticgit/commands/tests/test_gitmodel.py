import os
import json

from StringIO import StringIO
from uuid import uuid4
from elasticgit.commands.gitmodel import MigrateGitModelRepo
from elasticgit.commands import avro
from elasticgit.tests.base import ToolBaseTest
from contextlib import contextmanager


class TestMigrateGitModelRepo(ToolBaseTest):

    def setUp(self):
        self.workspace = self.mk_workspace()

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

    def mk_gitmodel_migrator(self):
        stdouts = {}

        @contextmanager
        def patched_get_fileopener(dir_path, ignored_flags):
            file_name = os.path.basename(dir_path)
            model_name, _, _ = file_name.split('.', 3)
            yield stdouts.setdefault(model_name, StringIO())

        migrator = MigrateGitModelRepo()
        migrator.file_opener = patched_get_fileopener
        return migrator, stdouts

    def assertFields(self, schema, fields):
        for key, value in fields:
            [schema_field] = [field
                              for field in schema['fields']
                              if field['name'] == key]
            self.assertEqual(
                schema_field['type'], value,
                'Field: %r, expected type %r got %r.' % (
                    key, value, schema_field['type']))

    def test_introspect_category_schema(self):
        self.mk_gitmodel_category_data(self.workspace)
        migrator, stdouts = self.mk_gitmodel_migrator()
        migrator.run(self.workspace.repo.working_dir, 'migrated')
        json_schema = stdouts['GitCategoryModel'].getvalue()
        schema = json.loads(json_schema)
        self.assertEqual(schema['name'], 'GitCategoryModel')
        self.assertEqual(schema['namespace'], 'migrated')
        self.assertEqual(schema['type'], 'record')
        self.assertFields(schema, [
            ('subtitle', 'string'),
            ('language', 'string'),
            ('title', 'string'),
            ('slug', 'string'),
            ('source', 'string'),  # inferred null but default type is string
            ('position', 'int'),
            ('featured_in_navbar', 'boolean'),
            ('id', 'string'),
        ])

    def test_migrate_category_data(self):
        category_uuid = self.mk_gitmodel_category_data(self.workspace)
        migrator, stdouts = self.mk_gitmodel_migrator()
        # using ``__module__`` as the module_name so the workspace
        # is able to load the dynamically generatd classes out of module
        # again
        schema, records = migrator.run(
            self.workspace.repo.working_dir, self.__module__)
        model_class = avro.deserialize(schema, module_name=self.__module__)
        [record] = records
        self.assertEqual(record.uuid, category_uuid)
        [reindexed] = self.workspace.reindex(model_class)
        self.workspace.refresh_index()
        [result] = self.workspace.S(model_class).everything()
        self.assertEqual(model_class.__name__, 'GitCategoryModel')
        self.assertTrue(
            category_uuid == record.uuid == reindexed.uuid == result.uuid)
        self.assertTrue(
            dict(record) ==
            dict(reindexed) ==
            dict(result.get_object()))

    def test_introspect_page_schema(self):
        self.mk_gitmodel_page_data(self.workspace)
        migrator, stdouts = self.mk_gitmodel_migrator()
        migrator.run(self.workspace.repo.working_dir, 'migrated')
        json_schema = stdouts['GitPageModel'].getvalue()
        schema = json.loads(json_schema)
        self.assertEqual(schema['name'], 'GitPageModel')
        self.assertEqual(schema['namespace'], 'migrated')
        self.assertEqual(schema['type'], 'record')
        self.assertFields(schema, [
            ('subtitle', 'string'),
            ('description', 'string'),
            ('language', 'string'),
            ('title', 'string'),
            ('primary_category', 'string'),
            ('created_at', 'string'),
            ('featured_in_category', 'boolean'),
            ('modified_at', 'string'),
            ('linked_pages', {
                'type': 'array',
                'items': ['string'],
            }),
            ('slug', 'string'),
            ('content', 'string'),
            ('source', 'string'),  # inferred null but default type is string
            ('featured', 'boolean'),
            ('published', 'boolean'),
            ('position', 'int'),
            ('id', 'string')
        ])

    def test_migrate_page_data(self):
        page_uuid = self.mk_gitmodel_page_data(self.workspace)
        migrator, stdouts = self.mk_gitmodel_migrator()
        # using ``__module__`` as the module_name so the workspace
        # is able to load the dynamically generatd classes out of module
        # again
        schema, records = migrator.run(
            self.workspace.repo.working_dir, self.__module__)
        model_class = avro.deserialize(schema, module_name=self.__module__)
        [record] = records
        self.assertEqual(record.uuid, page_uuid)
        [reindexed] = self.workspace.reindex(model_class)
        self.workspace.refresh_index()
        [result] = self.workspace.S(model_class).everything()
        self.assertEqual(model_class.__name__, 'GitPageModel')
        self.assertTrue(
            page_uuid == record.uuid == reindexed.uuid == result.uuid)
        self.assertTrue(
            dict(record) ==
            dict(reindexed) ==
            dict(result.get_object()))
