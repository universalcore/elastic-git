from jinja2 import Environment, PackageLoader
from functools import partial
import argparse
import imp
import json
import pprint

from datetime import datetime

from elasticgit.models import (
    Model, IntegerField, TextField, ModelVersionField, FloatField,
    BooleanField, ListField, DictField, UUIDField)

from elasticgit.commands.base import (
    ToolCommand, ToolCommandError, CommandArgument)
from elasticgit.utils import load_class


def deserialize(schema, mapping={}, module_name=None):
    """
    Deserialize an Avro schema and define it within a module (if specified)

    :param dict schema:
        The Avro schema
    :param dict mapping:
        Optional mapping to override the default mapping.
    :param str module_name:
        The name of the module to put this in. This module is dynamically
        generated with :py:func:`imp.new_module` and only available
        during code generation for setting the class' ``__module__``.
    :returns:
        :py:class:`elasticgit.models.Model`

    >>> from elasticgit.commands.avro import deserialize
    >>> schema = {
    ... 'name': 'Foo',
    ... 'type': 'record',
    ... 'fields': [{
    ...         'name': 'some_field',
    ...         'type': 'int',
    ...     }]
    ... }
    >>> deserialize(schema)
    <class 'Foo'>
    >>>

    """
    schema_loader = SchemaLoader()
    model_code = schema_loader.generate_model(schema)
    model_name = schema['name']

    if module_name is not None:
        mod = imp.new_module(module_name)
        scope = mod.__dict__
    else:
        scope = {}

    exec model_code in scope

    return scope.pop(model_name)


def serialize(model_class):
    """
    Serialize a :py:class:`elasticgit.models.Model` to an Avro JSON schema

    :param elasticgit.models.Model model_class:
    :returns: str

    >>> from elasticgit.commands.avro import serialize
    >>> from elasticgit.tests.base import TestPerson
    >>> json_data = serialize(TestPerson)
    >>> import json
    >>> schema = json.loads(json_data)
    >>> sorted(schema.keys())
    [u'fields', u'name', u'namespace', u'type']
    >>>

    """
    schema_dumper = SchemaDumper()
    return schema_dumper.dump_schema(model_class)


class FieldMapType(object):
    """
    A custom type for providing mappings on the command line for the
    :py:class:`.SchemaLoader` tool.

    :param str mapping:
        A mapping of a key to a field type

    >>> from elasticgit.commands.avro import FieldMapType
    >>> mt = FieldMapType('uuid=elasticgit.models.UUIDField')
    >>> mt.key
    'uuid'
    >>> mt.field_class
    <class 'elasticgit.models.UUIDField'>
    >>>

    """
    def __init__(self, mapping):
        key, _, class_name = mapping.partition('=')
        self.key = key
        self.field_class = load_class(class_name)


class SchemaLoader(ToolCommand):
    """
    Load an Avro_ JSON schema and generate Elasticgit Model python code.

    ::

        python -m elasticgit.tools load-schema avro.json

    .. _Avro: avro.apache.org/docs/1.7.7/spec.html


    """

    command_name = 'load-schema'
    command_help_text = 'Dump an Avro schema as an Elasticgit model.'
    command_arguments = (
        CommandArgument(
            'schema_files',
            metavar='schema_file',
            help='path to Avro schema file.',
            nargs='+', type=argparse.FileType('r')),
        CommandArgument(
            '-m', '--map-field',
            help=(
                'Manually map specific field names to Field classes. '
                'Formatted as ``field=IntegerField``'
            ),
            metavar='key=FieldType',
            dest='manual_mappings',
            action='append', type=FieldMapType)
    )

    mapping = {
        'int': IntegerField,
        'string': TextField,
        'float': FloatField,
        'boolean': BooleanField,
        'array': ListField,
        'record': DictField,
    }

    def run(self, schema_files, manual_mappings=None):
        """
        Inspect an Avro schema file and write the generated Python code
        to ``self.stdout``

        :param list schema_files:
            The list of file pointers to load.
        :param list manual_mappings:
            A list of :py:class:`.FieldMapType` types that allow
            overriding of field mappings.
        """
        if manual_mappings:
            mapping = dict((m.key, m.field_class) for m in manual_mappings)
        else:
            mapping = []

        schemas = [json.load(schema_fp) for schema_fp in schema_files]
        self.stdout.write(self.generate_models(schemas, mapping=mapping))

    def field_class_for(self, field, manual_mapping):
        field_type = field['type']
        field_key = field['name']

        if field_key in manual_mapping:
            return manual_mapping[field_key].__name__

        if isinstance(field_type, dict):
            return self.field_class_for_complex_type(field)
        return self.mapping[field_type].__name__

    def field_class_for_complex_type(self, field):
        field_type = field['type']
        if (field_type['name'] == 'ModelVersionField' and
                field_type['namespace'] == 'elasticgit.models'):
            return ModelVersionField.__name__
        return DictField.__name__

    def default_value(self, field):
        return pprint.pformat(field['default'], indent=8)

    def generate_models(self, schemas, mapping={}):
        """
        Generate Python code for the given Avro schemas

        :param list schemas:
            A list of Avro schema's
        :param dict mapping:
            An optional mapping of keys to field types that can be
            used to override the default mapping.
        :returns: str
        """
        first, remainder = schemas[0], schemas[1:]
        first_chunk = self.generate_model(first, mapping)
        remainder_chunk = u''.join([
            self.generate_model(subsequent, mapping, include_header=False)
            for subsequent in remainder])
        return u'\n'.join([
            first_chunk,
            remainder_chunk,
        ])

    def generate_model(self, schema, mapping={}, include_header=True):
        """
        Generate Python code for the given Avro schema

        :param dict schema:
            The Avro schema
        :param dict mapping:
            An optional mapping of keys to field types that can be
            used to override the default mapping.
        :parak bool include_header:
            Whether or not to generate the header in the source code,
            this is useful of you're generating a list of model schema
            but don't want the header and import statements printed
            every time.
        :returns: str
        """
        env = Environment(loader=PackageLoader('elasticgit', 'templates'))
        env.globals['field_class_for'] = partial(
            self.field_class_for, manual_mapping=mapping)
        env.globals['default_value'] = self.default_value

        template = env.get_template('model_generator.py.txt')
        return template.render(
            datetime=datetime.utcnow(),
            schema=schema,
            include_header=include_header)


class SchemaDumper(ToolCommand):
    """
    Dump an Avro_ JSON schema for an Elasticgit Model.

    ::

        python -m elasticgit.tools dump-schema elasticgit.tests.base.TestPerson

    .. _Avro: avro.apache.org/docs/1.7.7/spec.html

    """

    command_name = 'dump-schema'
    command_help_text = 'Dump model information as an Avro schema.'
    command_arguments = (
        CommandArgument('class_path', help='python path to Class.'),
    )

    mapping = {
        IntegerField: 'int',
        TextField: 'string',
        FloatField: 'float',
        BooleanField: 'boolean',
        ListField: 'array',
        DictField: 'record',
        UUIDField: 'string',
        ModelVersionField: {
            'type': 'record',
            'name': 'ModelVersionField',
            'namespace': 'elasticgit.models',
            'fields': [
                {
                    'name': 'language',
                    'type': 'string',
                },
                {
                    'name': 'language_version_string',
                    'type': 'string',
                },
                {
                    'name': 'language_version',
                    'type': 'string',
                },
                {
                    'name': 'package',
                    'type': 'string',
                },
                {
                    'name': 'package_version',
                    'type': 'string',
                }
            ]
        }
    }

    def run(self, class_path):
        """
        Introspect the given class path and print the schema to
        `self.stdout`

        :param str class_path:
            The path to the model file to introspect
        """
        module_path, name = class_path.rsplit('.', 1)
        parent_module = __import__(module_path, fromlist=[name])
        model_class = getattr(parent_module, name)

        if not issubclass(model_class, Model):
            raise ToolCommandError(
                '%r is not a subclass of %r' % (model_class, Model))
        return self.stdout.write(self.dump_schema(model_class))

    def dump_schema(self, model_class):
        """
        Return the JSON schema for an :py:class:`elasticgit.models.Model`.

        :param elasticgit.models.Model model_class:
        :returns: str
        """
        return json.dumps({
            'type': 'record',
            'namespace': model_class.__module__,
            'name': model_class.__name__,
            'fields': [self.get_field_info(name, field)
                       for name, field in model_class._fields.items()],
        }, indent=2)

    def get_field_info(self, name, field):
        """
        Return the Avro field object for an
        :py:class:`elasticgit.models.Model` field.

        :param str name:
            The name of the field
        :param confmodel.fields.ConfigField field:
            The field
        :returns: dict
        """
        return {
            'name': name,
            'type': self.mapping[field.__class__],
            'doc': field.doc,
            'default': field.default,
            'aliases': [fallback.field_name for fallback in field.fallbacks]
        }
