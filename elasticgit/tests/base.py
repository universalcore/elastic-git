from unittest import TestCase

from elasticgit.models import Model
from elasticgit.manager import EG


class ModelBaseTest(TestCase):

    def mk_model(self, fields):
        return type('TempModel', (Model,), fields)

    def mk_workspace(self, repo='.test_repo', url='https://localhost',
                     index_name='test-repo-index'):
        return EG.workspace(repo, es={
            'urls': [url],
        }, index_name=index_name)
