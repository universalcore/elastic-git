from unittest import TestCase

from elasticgit.models import Model
from elasticgit.manager import EG


class ModelBaseTest(TestCase):

    def mk_model(self, fields):
        return type('TempModel', (Model,), fields)

    def mk_instance(self, data):
        model_class = self.mk_model(dict([
            (field_name, field_class(field_name))
            for field_name, field_class, field_value in data
        ]))

        return model_class(dict([
            (field_name, field_value)
            for field_name, field_class, field_value in data
        ]))

    def mk_workspace(self, repo='../.test_repo/', url='https://localhost',
                     index_name='test-repo-index'):
        workspace = EG.workspace(repo, es={
            'urls': [url],
        }, index_name=index_name)
        return workspace
