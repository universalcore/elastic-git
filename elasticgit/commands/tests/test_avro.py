# -*- coding: utf-8 -*-
import json

import avro.schema
from avro.datafile import DataFileReader, DataFileWriter
from avro.io import DatumReader, DatumWriter

from elasticgit import models
from elasticgit.tests.base import ToolBaseTest


class TestDumpSchemaTool(ToolBaseTest):

    def test_dump_schema(self):
        schema_dumper = self.mk_schema_dumper()
        schema_dumper.run(
            class_path='elasticgit.tests.base.TestPerson')
        schema = self.get_schema(schema_dumper)
        self.assertEqual(schema['type'], 'record')
        self.assertEqual(schema['name'], 'TestPerson')
        self.assertEqual(schema['namespace'], 'elasticgit.tests.base')

    def test_dump_default_value(self):
        class TestModel(models.Model):
            age = models.IntegerField('The age', default=20)

        schema_dumper = self.mk_schema_dumper()
        schema = json.loads(schema_dumper.dump_schema(TestModel))
        age = self.get_field(schema, 'age')
        self.assertEqual(age['default'], 20)

    def test_dump_doc(self):
        class TestModel(models.Model):
            age = models.IntegerField('The age', default=20)

        schema_dumper = self.mk_schema_dumper()
        schema = json.loads(schema_dumper.dump_schema(TestModel))
        age = self.get_field(schema, 'age')
        self.assertEqual(age['doc'], 'The age')

    def test_dump_fallback_value(self):
        class TestModel(models.Model):
            age = models.IntegerField(
                'The age', default=20,
                fallbacks=[models.SingleFieldFallback('length')])

        schema_dumper = self.mk_schema_dumper()
        schema = json.loads(schema_dumper.dump_schema(TestModel))
        age = self.get_field(schema, 'age')
        self.assertEqual(age['aliases'], ['length'])

    def test_dump_array(self):
        class TestModel(models.Model):
            tags = models.ListField('The tags',
                                    fields=(models.IntegerField('doc'),))

        schema_dumper = self.mk_schema_dumper()
        schema = json.loads(schema_dumper.dump_schema(TestModel))
        tags = self.get_field(schema, 'tags')
        field_type = tags['type']
        self.assertEqual(field_type['type'], 'array')
        self.assertEqual(set(field_type['items']), set(['null', 'int']))


class TestLoadSchemaTool(ToolBaseTest):

    def assertFieldNames(self, model_class, *field_names):
        self.assertEqual(
            set(model_class._fields.keys()),
            set(['uuid', '_version'] + list(field_names)))

    def assertField(self, model_class, field_name, default=None, doc=None,
                    field_type=None):
        self.assertFieldNames(model_class, field_name)
        fields = model_class._fields
        if default is not None:
            self.assertEqual(fields[field_name].default, default)
        if doc is not None:
            self.assertEqual(fields[field_name].doc, doc)
        if field_type is not None:
            self.assertTrue(
                isinstance(fields[field_name], field_type),
                'Field %s is of type %r, was expecting %r' % (
                    field_name, type(fields[field_name]), field_type,))

    def assertFieldCreation(self, field, field_type, field_mapping={}):
        model_class = self.load_class_with_field(
            field, field_mapping=field_mapping)
        self.assertField(model_class, field['name'], field['default'],
                         field['doc'], field_type)

    def test_model_renames(self):
        model_class = self.load_class_with_field(
            {
                'name': 'age',
                'type': 'int',
                'doc': 'The Age',
                'default': 10,
            },
            model_name='OldModel',
            model_renames={
                'OldModel': 'NewModel',
            })
        self.assertEqual(model_class.__name__, 'NewModel')

    def test_integer_field(self):
        self.assertFieldCreation({
            'name': 'age',
            'type': 'int',
            'doc': 'The Age',
            'default': 10,
        }, models.IntegerField)

    def test_float_field(self):
        self.assertFieldCreation({
            'name': 'age',
            'type': 'float',
            'doc': 'The Age',
            'default': 10.0,
        }, models.FloatField)

    def test_string_field(self):
        self.assertFieldCreation({
            'name': 'name',
            'type': 'string',
            'doc': 'The Name',
            'default': 'Test Kees',
        }, models.TextField)

    def test_boolean_field(self):
        self.assertFieldCreation({
            'name': 'boolean',
            'type': 'boolean',
            'doc': 'The Boolean',
            'default': False,
        }, models.BooleanField)

    def test_array_field(self):
        self.assertFieldCreation({
            'name': 'array',
            'type': {
                'type': ['null', 'array'],
                'items': ['string'],
            },
            'doc': 'The Array',
            'default': ['foo', 'bar', 'baz']
        }, models.ListField)

    def test_dict_field(self):
        self.assertFieldCreation({
            'name': 'obj',
            'type': {
                'type': 'record',
                'items': ['string'],
                'fields': [{
                    'name': 'hello',
                    'type': ['null', 'string'],
                }]
            },
            'doc': 'The Object',
            'default': {'hello': 'world'},
        }, models.DictField)

    def test_complex_field(self):
        self.assertFieldCreation({
            'name': 'complex',
            'type': {
                'namespace': 'foo.bar',
                'name': 'ItIsComplicated',
                'type': 'record',
                'items': ['string'],
                'fields': [{
                    'name': 'foo',
                    'type': ['null', 'string'],
                }]
            },
            'doc': 'Super Complex',
            'default': {},
        }, models.DictField)

    def test_version_field(self):
        self.assertFieldCreation({
            'name': 'version',
            'type': {
                'namespace': 'elasticgit.models',
                'name': 'version',
                'type': 'record',
                'items': ['string'],
            },
            'doc': 'The Model Version',
            'default': models.version_info,
        }, models.DictField)

    def test_mapping_hints(self):
        self.assertFieldCreation({
            'name': 'uuid',
            'type': 'string',
            'doc': 'The Name',
            'default': 'Test Kees',
        }, models.UUIDField, field_mapping={
            'uuid': models.UUIDField
        })


class DumpAndLoadModel(models.Model):
    text = models.TextField('the näme')
    integer = models.IntegerField('the integer')
    float_ = models.FloatField('the float')
    boolean = models.BooleanField('the boolean')
    list_ = models.ListField('the list', fields=(
        models.IntegerField('the int'),
    ))
    dict_ = models.DictField('the dict', fields=(
        models.TextField('hello', name='hello'),
    ))


class TestDumpAndLoad(ToolBaseTest):

    def test_two_way(self):

        schema_dumper = self.mk_schema_dumper()
        schema_loader = self.mk_schema_loader()

        schema = schema_dumper.dump_schema(DumpAndLoadModel)

        generated_code = schema_loader.generate_model(json.loads(schema))

        GeneratedModel = self.load_class(generated_code, 'DumpAndLoadModel')

        data = {
            'text': 'the text',
            'integer': 1,
            'float': 1.1,
            'boolean': False,
            'list_': [1, 2, 3],
            'dict_': {'hello': 'world'}
        }
        record1 = DumpAndLoadModel(data)
        record2 = GeneratedModel(data)
        self.assertEqual(record1, record2)

    def test_two_way_dict_ints(self):

        schema_dumper = self.mk_schema_dumper()
        schema_loader = self.mk_schema_loader()

        schema = schema_dumper.dump_schema(DumpAndLoadModel)
        generated_code = schema_loader.generate_model(json.loads(schema))

        GeneratedModel = self.load_class(generated_code, 'DumpAndLoadModel')

        data = {
            'text': 'the text',
            'integer': 1,
            'float': 1.1,
            'boolean': False,
            'list_': [1, 2, 3],
            'dict_': {'hello': '1'}
        }
        record1 = DumpAndLoadModel(data)
        record2 = GeneratedModel(data)
        self.assertEqual(record1, record2)

    def test_two_way_list_ints(self):

        schema_dumper = self.mk_schema_dumper()
        schema_loader = self.mk_schema_loader()

        schema = schema_dumper.dump_schema(DumpAndLoadModel)
        generated_code = schema_loader.generate_model(json.loads(schema))

        GeneratedModel = self.load_class(generated_code, 'DumpAndLoadModel')

        data = {
            'text': 'the text',
            'integer': 1,
            'float': 1.1,
            'boolean': False,
            'list_': [1, 2, 3],
            'dict_': {'hello': '1'}
        }
        record1 = DumpAndLoadModel(data)
        record2 = GeneratedModel(data)
        self.assertEqual(record1, record2)

    def test_two_way_list_unicode(self):

        schema_dumper = self.mk_schema_dumper()
        schema_loader = self.mk_schema_loader()

        schema = schema_dumper.dump_schema(DumpAndLoadModel)
        generated_code = schema_loader.generate_model(json.loads(schema))

        GeneratedModel = self.load_class(generated_code, 'DumpAndLoadModel')

        data = {
            'text': 'lørëm îpsüm',
            'integer': 1,
            'float': 1.1,
            'boolean': False,
            'list_': [1, 2, 3],
            'dict_': {'hello': '1'}
        }
        record1 = DumpAndLoadModel(data)
        record2 = GeneratedModel(data)
        self.assertEqual(record1, record2)

    def test_single_fallback(self):
        class Foo(models.Model):
            field = models.TextField(
                'the field',
                fallbacks=[models.SingleFieldFallback('old_field')])
            old_field = models.TextField(
                'the old field', required=False)

        schema_dumper = self.mk_schema_dumper()
        schema_loader = self.mk_schema_loader()

        schema = schema_dumper.dump_schema(Foo)
        generated_code = schema_loader.generate_model(json.loads(schema))

        GeneratedFoo = self.load_class(generated_code, 'Foo')
        self.assertEqual(
            GeneratedFoo({'old_field': 'the value'}).field,
            'the value')
        self.assertEqual(
            GeneratedFoo({'field': 'the new value'}).field,
            'the new value')

    def test_multiple_fallbacks(self):
        class Foo(models.Model):
            field = models.TextField(
                'the field',
                fallbacks=[
                    models.SingleFieldFallback('old_field'),
                    models.SingleFieldFallback('even_older_field')])
            old_field = models.TextField(
                'the old field', required=False)
            even_older_field = models.TextField(
                'the oldest field', required=False)

        schema_dumper = self.mk_schema_dumper()
        schema_loader = self.mk_schema_loader()

        schema = schema_dumper.dump_schema(Foo)
        generated_code = schema_loader.generate_model(json.loads(schema))

        GeneratedFoo = self.load_class(generated_code, 'Foo')
        self.assertEqual(
            GeneratedFoo({'even_older_field': 'the original value'}).field,
            'the original value')
        self.assertEqual(
            GeneratedFoo({'old_field': 'the old value'}).field,
            'the old value')
        self.assertEqual(
            GeneratedFoo({'field': 'the new value'}).field,
            'the new value')

    def test_load_older_version(self):
        class Foo(models.Model):
            pass

        old_version_info = models.version_info.copy()
        old_version_info['package_version'] = '0.0.1'

        f = Foo({
            'uuid': 'the-uuid',
            '_version': old_version_info,
        })
        self.assertEqual(f.uuid, 'the-uuid')
        self.assertEqual(f._version['package_version'], '0.0.1')

    def test_load_newer_version(self):
        class Foo(models.Model):
            pass

        major, minor, micro = map(
            int, models.version_info['package_version'].split('.'))

        new_version = models.version_info.copy()
        new_version['package_version'] = '%d.%d.%d' % (
            major + 1,
            minor,
            micro)
        self.assertRaises(models.ConfigError, Foo, {
            'uuid': 'the-uuid',
            '_version': new_version,
        })


class TestAvroDataWriter(ToolBaseTest):

    def binary_roundtrip(self, model_class, data):
        model = model_class(data)
        schema_dumper = self.mk_schema_dumper()
        schema = avro.schema.parse(schema_dumper.dump_schema(model_class))

        fp, file_name = self.get_tempfile(text=False)
        with DataFileWriter(fp, DatumWriter(), schema) as writer:
            writer.append(dict(model))

        with DataFileReader(
                open(file_name, 'rb'),
                DatumReader(readers_schema=schema)) as reader:
            [row] = reader
            return row

    def assertBinaryRoundTrip(self, model_class, data):
        round_tripped = self.binary_roundtrip(model_class, data)
        self.assertEqual(model_class(data), model_class(round_tripped))

    def test_empty_model(self):

        class Foo(models.Model):
            pass

        self.assertBinaryRoundTrip(Foo, {})

    def test_list_model(self):
        class Foo(models.Model):
            list_ = models.ListField(
                'list field!', fields=(models.IntegerField('ints!'),))

        self.assertBinaryRoundTrip(Foo, {'list_': [1, 2, 3]})

    def test_dict_model(self):
        class Foo(models.Model):
            dict_ = models.DictField(
                'dict field!', fields=(
                    models.IntegerField('ints', name='int'),
                    models.TextField('texts', name='text'),
                )
            )

        self.assertBinaryRoundTrip(
            Foo, {'dict_': {'int': 1, 'text': 'texts'}})

    def test_null_fields(self):
        class Foo(models.Model):
            name = models.TextField('name')
            age = models.IntegerField('age', default=5)

        data = self.binary_roundtrip(Foo, {})
        model = Foo(data)
        self.assertEqual(model.age, 5)
        self.assertEqual(model.name, None)
