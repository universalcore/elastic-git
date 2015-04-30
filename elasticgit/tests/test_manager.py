# -*- coding: utf-8 -*-

import os

from elasticgit import EG
from elasticgit.models import IntegerField
from elasticgit.tests.base import ModelBaseTest, TestPage, TestPerson

from elasticsearch.client import Elasticsearch


class TestManager(ModelBaseTest):

    def setUp(self):
        self.workspace = self.mk_workspace()

    def test_workspace(self):
        workspace = self.mk_workspace(name='.foo')
        self.assertTrue(isinstance(workspace.im.es, Elasticsearch))
        self.assertEqual(os.path.basename(workspace.repo.working_dir), '.foo')

    def test_index_prefix(self):
        repo_path = os.path.join(self.WORKING_DIR, 'bar')
        workspace = EG.workspace(repo_path)
        self.addCleanup(workspace.destroy)
        self.assertEqual(workspace.index_prefix, 'bar')

    def test_mapping_type(self):
        model_class = self.mk_model({
            'age': IntegerField('An age')
        })
        mapping_type = self.workspace.im.get_mapping_type(model_class)
        self.assertEqual(
            mapping_type.get_index(),
            '%s-%s' % (
                self.workspace.index_prefix,
                self.workspace.repo.active_branch.name))
        self.assertEqual(mapping_type.get_model(), model_class)
        self.assertEqual(
            mapping_type.get_mapping_type_name(),
            'confmodel-config-TempModelType')

    def test_indexable(self):
        model_class = self.mk_model({
            'age': IntegerField('An age')
        })
        mapping_type = self.workspace.im.get_mapping_type(model_class)
        self.assertEqual(mapping_type.get_es(), self.workspace.im.es)
        self.assertEqual(mapping_type.get_mapping(), {
            'properties': {
                'age': {'type': 'integer'},
                'uuid': {'type': 'string'},
                '_version': model_class._fields['_version'].mapping,
            }
        })
        model_instance = model_class({'age': 1})
        self.assertEqual(
            mapping_type.extract_document('foo', model_instance)['age'],
            1)

    def test_get_indexable(self):
        model_class = self.mk_model({
            'age': IntegerField('An age')
        })
        mapping_type = self.workspace.im.get_mapping_type(model_class)
        self.assertEqual(list(mapping_type.get_indexable()), [])

    def test_write_config(self):
        sm = self.workspace.sm
        user_data = {'name': 'test', 'email': 'email@example.org'}
        sm.write_config('user', user_data)
        self.assertEqual(sm.read_config('user'), user_data)

    def test_setup_mapping(self):
        MappingType = self.workspace.im.get_mapping_type(TestPage)
        self.assertTrue(
            self.workspace.setup_mapping(TestPage))
        self.assertEqual(
            self.workspace.get_mapping(TestPage),
            MappingType.get_mapping())

    def test_setup_custom_mapping(self):
        self.assertTrue(
            self.workspace.setup_custom_mapping(TestPerson, {
                'properties': {
                    'name': {
                        'type': 'string',
                        'index': 'not_analyzed',
                    },
                    'age': {
                        'type': 'integer'
                    }
                }
            }))

        post_mapping_person = TestPerson({'age': 10, 'name': 'eng_UK'})
        self.workspace.save(post_mapping_person, 'Post-mapping save')
        self.workspace.refresh_index()
        self.assertEqual(
            self.workspace.S(TestPerson).filter(name='eng_UK').count(), 1)

    def test_save_bytestring(self):
        p = TestPerson({'age': 10, 'name': 'Name'})
        self.workspace.save(p, 'bytestring')
        repo = self.workspace.repo
        [save_commit, _] = repo.iter_commits()
        self.assertEqual(save_commit.message, 'bytestring')

    def test_save_unidecode(self):
        p = TestPerson({'age': 10, 'name': 'Name'})
        self.workspace.save(p, u'Unîcødé')
        repo = self.workspace.repo
        [save_commit, _] = repo.iter_commits()
        self.assertEqual(save_commit.message, 'Unicode')

    def test_delete_bytestring(self):
        p = TestPerson({'age': 10, 'name': 'Name'})
        self.workspace.save(p, 'save bytestring')
        self.workspace.delete(p, 'delete bytestring')
        repo = self.workspace.repo
        [delete_commit, save_commit, _] = repo.iter_commits()
        self.assertEqual(save_commit.message, 'save bytestring')
        self.assertEqual(delete_commit.message, 'delete bytestring')

    def test_delete_unidecode(self):
        p = TestPerson({'age': 10, 'name': 'Name'})
        self.workspace.save(p, u'Sävé Unîcødé')
        self.workspace.delete(p, u'Délëtê Unîcødé')
        repo = self.workspace.repo
        [delete_commit, save_commit, _] = repo.iter_commits()
        self.assertEqual(save_commit.message, 'Save Unicode')
        self.assertEqual(delete_commit.message, 'Delete Unicode')
