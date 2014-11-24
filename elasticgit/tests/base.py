import os
import json
import tempfile
import shutil

from StringIO import StringIO

from unittest import TestCase

from elasticgit.models import (
    IntegerField, TextField, Model, SingleFieldFallback)
from elasticgit.workspace import EG
from elasticgit.utils import fqcn
from elasticgit.commands.avro import (
    SchemaDumper, SchemaLoader, FieldMapType, RenameType)


class TestPerson(Model):
    age = IntegerField('The Age')
    name = TextField('The name')


class TestPage(Model):
    title = TextField('The title')
    slug = TextField('The slug', mapping={'index': 'not_analyzed'})
    language = TextField('The language', mapping={'index': 'not_analyzed'})


class TestFallbackPerson(Model):
    age = IntegerField('The Age')
    name = TextField('The name', fallbacks=[
        SingleFieldFallback('nick'),
        SingleFieldFallback('obsolete'),
    ])
    nick = TextField('The nickname', required=False)
    obsolete = TextField('Some obsolete field', required=False)


class ModelBaseTest(TestCase):

    destroy = 'KEEP_REPO' not in os.environ
    WORKING_DIR = '.test_repos/'

    def mk_model(self, fields):
        return type('TempModel', (Model,), fields)

    def mk_index_prefix(self):
        long_name = self.id().split('.')
        class_name, test_name = long_name[-2], long_name[-1]
        index_prefix = '%s-%s' % (class_name, test_name)
        return index_prefix.lower()

    def mk_workspace(self, working_dir=None,
                     name=None,
                     url='http://localhost',
                     index_prefix=None,
                     auto_destroy=None,
                     initial_commit=True):
        working_dir = working_dir or self.WORKING_DIR
        name = name or self.id()
        index_prefix = index_prefix or self.mk_index_prefix()
        auto_destroy = auto_destroy or self.destroy
        workspace = EG.workspace(os.path.join(working_dir, name), es={
            'urls': [url],
        }, index_prefix=index_prefix)
        if auto_destroy:
            self.addCleanup(workspace.destroy)

        if initial_commit:
            index = workspace.repo.index
            index.commit('Initial Commit')

        return workspace


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

    def mk_tempdir(self):
        abs_path = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(abs_path))
        return abs_path

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

    def load_schema(self, data, field_mapping={}, model_renames={}):
        loader = self.mk_schema_loader()
        tmp_file = self.mk_tempfile(json.dumps(data, indent=2))
        with open(tmp_file, 'r') as fp:
            loader.run(
                [fp],
                field_mappings=[
                    FieldMapType('%s=%s' % (key, fqcn(value)))
                    for key, value in field_mapping.items()
                ],
                model_renames=[
                    RenameType('%s=%s' % (old, new))
                    for old, new in model_renames.items()
                ])
            return loader.stdout.getvalue()

    def load_field(self, field, model_name,
                   field_mapping={}, model_renames={}):
        return self.load_schema({
            'name': model_name,
            'namespace': 'some.module',
            'type': 'record',
            'fields': [field]
        }, field_mapping=field_mapping, model_renames=model_renames)

    def load_class(self, code_string, name):
        scope = {}
        exec code_string in scope
        return scope.pop(name)

    def load_class_with_field(self, field, field_mapping={}, model_renames={},
                              model_name='GeneratedModel'):
        model_code = self.load_field(field,
                                     model_name,
                                     field_mapping=field_mapping,
                                     model_renames=model_renames)
        model_name = model_renames.get(model_name, model_name)
        return self.load_class(model_code, model_name)
