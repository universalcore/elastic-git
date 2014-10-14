import os

from unittest import TestCase

from elasticgit.models import (
    IntegerField, TextField, Model, SingleFieldFallback)
from elasticgit.manager import EG


class ModelBaseTest(TestCase):

    def mk_model(self, fields):
        return type('TempModel', (Model,), fields)

    def mk_workspace(self, working_dir='.test_repos/',
                     name=None,
                     url='https://localhost',
                     index_prefix='test-repo-index',
                     auto_destroy=True):
        name = name or self.id()
        workspace = EG.workspace(os.path.join(working_dir, name), es={
            'urls': [url],
        }, index_prefix=index_prefix)
        if auto_destroy:
            self.addCleanup(workspace.destroy)
        return workspace


class TestPerson(Model):
    age = IntegerField('The Age')
    name = TextField('The name')


class TestFallbackPerson(Model):
    age = IntegerField('The Age')
    name = TextField('The name', fallbacks=[
        SingleFieldFallback('nick'),
        SingleFieldFallback('obsolete'),
    ])
    nick = TextField('The nickname', required=False)
    obsolete = TextField('Some obsolete field', required=False)
