from elasticgit.tests.base import ModelBaseTest

from elasticgit.models import IntegerField
from elasticsearch.client import Elasticsearch


class TestManager(ModelBaseTest):

    def test_workspace(self):
        workspace = self.mk_workspace()
        self.assertTrue(isinstance(workspace.index.es, Elasticsearch))
        self.assertEqual(workspace.workdir, '.test_repo')

    def test_mapping_type(self):
        model_class = self.mk_model({
            'age': IntegerField('An age')
        })
        workspace = self.mk_workspace()
        mapping_type = workspace.index.get_mapping_type(model_class)
        self.assertEqual(mapping_type.get_index(), 'test-repo-index')
        self.assertEqual(mapping_type.get_model(), model_class)
        self.assertEqual(
            mapping_type.get_mapping_type_name(),
            'confmodel.config.TempModel-type')

    def test_indexable(self):
        workspace = self.mk_workspace()
        model_class = self.mk_model({
            'age': IntegerField('An age')
        })
        mapping_type = workspace.index.get_mapping_type(model_class)
        self.assertEqual(mapping_type.get_es(), workspace.index.es)
        self.assertEqual(mapping_type.get_mapping(), {
            'properties': {
                'age': {'type': 'integer'}
            }
        })
        model_instance = model_class({'age': 1})
        self.assertEqual(
            mapping_type.extract_document('foo', model_instance),
            {'age': 1})

    def test_get_indexable(self):
        workspace = self.mk_workspace()
        model_class = self.mk_model({
            'age': IntegerField('An age')
        })
        mapping_type = workspace.index.get_mapping_type(model_class)
        self.assertEqual(list(mapping_type.get_indexable()), [])
