from elasticgit.tests.base import ModelBaseTest

from elasticgit.models import IntegerField
from elasticsearch.client import Elasticsearch


class TestManager(ModelBaseTest):

    def setUp(self):
        self.workspace = self.mk_workspace()
        self.workspace.setup('Test Kees', 'kees@example.org')

    def tearDown(self):
        if self.workspace.exists():
            self.workspace.destroy()

    def test_workspace(self):
        workspace = self.mk_workspace('.foo')
        self.assertTrue(isinstance(workspace.im.es, Elasticsearch))
        self.assertEqual(workspace.workdir, '.foo')

    def test_mapping_type(self):
        model_class = self.mk_model({
            'age': IntegerField('An age')
        })
        mapping_type = self.workspace.im.get_mapping_type(model_class)
        self.assertEqual(mapping_type.get_index(), 'test-repo-index')
        self.assertEqual(mapping_type.get_model(), model_class)
        self.assertEqual(
            mapping_type.get_mapping_type_name(),
            'confmodel__config___TempModelType')

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
