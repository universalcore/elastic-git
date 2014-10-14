import os
import json
import tempfile

from StringIO import StringIO

from unittest import TestCase

from elasticgit.models import (
    IntegerField, TextField, Model, SingleFieldFallback)
from elasticgit.manager import EG
from elasticgit.commands.avro import SchemaDumper, SchemaLoader


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


class ToolBaseTest(ModelBaseTest):

    def mk_schema_dumper(self):
        schema_dumper = SchemaDumper()
        schema_dumper.stdout = StringIO()
        return schema_dumper

    def get_schema(self, schema_dumper):
        return json.loads(schema_dumper.stdout.getvalue())

    def get_field(self, schema, field_name):
        return [field
                for field in schema['fields']
                if field['name'] == field_name][0]

    def mk_tempfile(self, data):
        fd, name = tempfile.mkstemp(text=True)
        with open(name, 'w') as fp:
            fp.write(data)
        self.addCleanup(lambda: os.unlink(name))
        os.close(fd)
        return name

    def mk_schema_loader(self):
        schema_loader = SchemaLoader()
        schema_loader.stdout = StringIO()
        return schema_loader

    def load_schema(self, data):
        loader = self.mk_schema_loader()
        loader.run(
            self.mk_tempfile(
                json.dumps(data, indent=2)))
        return loader.stdout.getvalue()

    def load_field(self, field, name):
        return self.load_schema({
            'name': name,
            'namespace': 'some.module',
            'type': 'record',
            'fields': [field]
        })

    def load_class(self, code_string, name):
        scope = {}
        exec code_string in scope
        return scope.pop(name)

    def load_class_with_field(self, field):
        name = 'GeneratedModel'
        model_code = self.load_field(field, name)
        return self.load_class(model_code, name)
