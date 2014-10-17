import os

from elasticgit.models import IntegerField, ModelVersionField
from elasticgit.tests.base import ModelBaseTest, TestPage, TestPerson

from elasticsearch.client import Elasticsearch


class TestManager(ModelBaseTest):

    def setUp(self):
        self.workspace = self.mk_workspace()
        self.workspace.setup('Test Kees', 'kees@example.org')

    def test_workspace(self):
        workspace = self.mk_workspace(name='.foo')
        self.assertTrue(isinstance(workspace.im.es, Elasticsearch))
        self.assertEqual(os.path.basename(workspace.repo.working_dir), '.foo')

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
                '_version': ModelVersionField.default_mapping,
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
