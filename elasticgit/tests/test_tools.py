import json
from StringIO import StringIO

from elasticgit.tests.base import ModelBaseTest
from elasticgit.models import Model, IntegerField, SingleFieldFallback
from elasticgit.tools import SchemaDumper


class TestDumpSchemaTool(ModelBaseTest):

    def setUp(self):
        self.workspace = self.mk_workspace()
        self.workspace.setup('Test Kees', 'kees@example.org')

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

    def test_dump_schema(self):
        schema_dumper = self.mk_schema_dumper()
        schema_dumper.run(
            class_path='elasticgit.tests.base.TestPerson')
        schema = self.get_schema(schema_dumper)
        self.assertEqual(schema['type'], 'record')
        self.assertEqual(schema['name'], 'TestPerson')
        self.assertEqual(schema['namespace'], 'elasticgit.tests.base')

    def test_dump_default_value(self):
        class TestModel(Model):
            age = IntegerField('The age', default=20)

        schema_dumper = self.mk_schema_dumper()
        schema_dumper.dump_schema(TestModel)
        schema = self.get_schema(schema_dumper)
        age = self.get_field(schema, 'age')
        self.assertEqual(age['default'], 20)

    def test_dump_fallback_value(self):
        class TestModel(Model):
            age = IntegerField(
                'The age', default=20,
                fallbacks=[SingleFieldFallback('length')])
            length = IntegerField(
                'The length', default=30)

        schema_dumper = self.mk_schema_dumper()
        schema_dumper.dump_schema(TestModel)
        schema = self.get_schema(schema_dumper)
        age = self.get_field(schema, 'age')
        self.assertEqual(age['aliases'], ['length'])
