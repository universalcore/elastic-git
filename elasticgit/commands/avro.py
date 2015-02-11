from jinja2 import Environment, PackageLoader
from functools import partial
import argparse
import imp
import json
import pprint

from datetime import datetime

from elasticgit import version_info
from elasticgit.models import (
    Model, IntegerField, TextField, ModelVersionField, FloatField,
    BooleanField, ListField, DictField, UUIDField)

from elasticgit.commands.base import (
    ToolCommand, ToolCommandError, CommandArgument)
from elasticgit.utils import load_class


def deserialize(schema, field_mapping={}, module_name=None):
    """
    Deserialize an Avro schema and define it within a module (if specified)

    :param dict schema:
        The Avro schema
    :param dict field_mapping:
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


class RenameType(object):
    """
    A custom type for renaming things.

    :param str mapping:
        A mapping of an old name to a new name

    >>> from elasticgit.commands.avro import RenameType
    >>> rt = RenameType('OldName=NewName')
    >>> rt.old
    'OldName'
    >>> rt.new
    'NewName'
    >>>
    """

    def __init__(self, mapping):
        self.old, _, self.new = mapping.partition('=')


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
            dest='field_mappings',
            action='append', type=FieldMapType),
        CommandArgument(
            '-r', '--rename-model',
            help=(
                'Manually rename a model.'
                'Formatted as ``OldModelName=NewShiny``'),
            metavar='OldModelName=NewShiny',
            dest='model_renames',
            action='append', type=RenameType),
    )

    core_mapping = {
        'int': IntegerField,
        'string': TextField,
        'float': FloatField,
        'boolean': BooleanField,
    }

    # How avro types map to Python types
    core_type_mappings = {
        'string': basestring,
        'null': None,
        'integer': int,
        'number': float,
        'record': dict,
        'array': list,
    }

    def run(self, schema_files, field_mappings=None, model_renames=None):
        """
        Inspect an Avro schema file and write the generated Python code
        to ``self.stdout``

        :param list schema_files:
            The list of file pointers to load.
        :param list field_mappings:
            A list of :py:class:`.FieldMapType` types that allow
            overriding of field mappings.
        :param list model_renames:
            A list of :py:class:`.RenameType` types that allow
            renaming of model names
        """
        field_mapping = dict((m.key, m.field_class)
                             for m in field_mappings or [])

        model_renames = dict((m.old, m.new)
                             for m in model_renames or [])

        schemas = [json.load(schema_fp) for schema_fp in schema_files]
        self.stdout.write(self.generate_models(
            schemas,
            field_mapping=field_mapping,
            model_renames=model_renames))

    def model_class_for(self, model_name, model_renames):
        return model_renames.get(model_name, model_name)

    def field_class_for(self, field, field_mapping):
        field_type = field['type']
        field_name = field['name']

        if field_name in field_mapping:
            return field_mapping[field_name].__name__

        if field_type == 'record' or isinstance(field_type, dict):
            return self.field_class_for_complex_type(field)
        return self.core_mapping[field_type].__name__

    def field_class_for_complex_type(self, field):
        field_type = field['type']
        handler = getattr(
            self, 'field_class_for_complex_%(type)s_type' % field_type)
        return handler(field)

    def field_class_for_complex_record_type(self, field):
        field_type = field['type']
        if (field_type.get('name') == 'ModelVersionField' and
                field_type.get('namespace') == 'elasticgit.models'):
            return ModelVersionField.__name__
        return DictField.__name__

    def field_class_for_complex_array_type(self, field):
        return ListField.__name__

    def default_value(self, field):
        return pprint.pformat(field['default'], indent=8)

    def generate_models(self, schemas, field_mapping={}, model_renames={}):
        """
        Generate Python code for the given Avro schemas

        :param list schemas:
            A list of Avro schema's
        :param dict field_mapping:
            An optional mapping of keys to field types that can be
            used to override the default mapping.
        :returns: str
        """
        first, remainder = schemas[0], schemas[1:]
        first_chunk = self.generate_model(first, field_mapping, model_renames)
        remainder_chunk = u''.join([
            self.generate_model(subsequent,
                                field_mapping,
                                model_renames,
                                include_header=False)
            for subsequent in remainder])
        return u'\n'.join([
            first_chunk,
            remainder_chunk,
        ])

    def generate_model(self, schema, field_mapping={}, model_renames={},
                       include_header=True):
        """
        Generate Python code for the given Avro schema

        :param dict schema:
            The Avro schema
        :param dict field_mapping:
            An optional mapping of keys to field types that can be
            used to override the default mapping.
        :param dict model_renames:
            An optional mapping of model names that can be used to
            rename a model.
        :parak bool include_header:
            Whether or not to generate the header in the source code,
            this is useful of you're generating a list of model schema
            but don't want the header and import statements printed
            every time.
        :returns: str
        """
        env = Environment(loader=PackageLoader('elasticgit', 'templates'))
        env.globals['model_class_for'] = partial(
            self.model_class_for, model_renames=model_renames)
        env.globals['field_class_for'] = partial(
            self.field_class_for, field_mapping=field_mapping)
        env.globals['default_value'] = self.default_value

        def python_types_for(field):
            return ', '.join([self.core_type_mappings[type_].__name__
                              for type_ in field['type']['items']])

        env.globals['types_for'] = python_types_for

        def is_complex(field):
            return (
                isinstance(field['type'], dict) or field['type'] == 'record')

        env.globals['is_complex'] = is_complex

        template = env.get_template('model_generator.py.txt')
        return template.render(
            datetime=datetime.utcnow(),
            schema=schema,
            include_header=include_header,
            version_info=version_info)


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

    # How model fields map to types
    core_field_mappings = {
        IntegerField: 'int',
        TextField: 'string',
        FloatField: 'float',
        BooleanField: 'boolean',
        UUIDField: 'string',
    }

    # How python types map to Avro types
    core_type_mappings = {
        basestring: 'string',
        str: 'string',
        unicode: 'string',
        None: 'null',
        int: 'integer',
        float: 'number',
        dict: 'record',
        list: 'array',
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

    def map_field_to_type(self, field):
        if field.__class__ in self.core_field_mappings:
            return self.core_field_mappings[field.__class__]

        handler = getattr(self, 'map_%s_type' % (field.__class__.__name__,))
        return handler(field)

    def map_ListField_type(self, field):
        avro_types = [self.core_type_mappings[type_]
                      for type_ in field.type_check.get_types()]
        return {
            'type': 'array',
            'items': avro_types
        }

    def map_DictField_type(self, field):
        avro_types = [self.core_type_mappings[type_]
                      for type_ in field.type_check.get_types()]
        return {
            'type': 'record',
            'items': avro_types,
        }

    def map_ModelVersionField_type(self, field):
        return {
            'type': 'record',
            'name': 'ModelVersionField',
            'namespace': 'elasticgit.models',
            'items': ['string'],
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
            ],
        }

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
            'type': self.map_field_to_type(field),
            'doc': field.doc,
            'default': field.default,
            'aliases': [fallback.field_name for fallback in field.fallbacks]
        }
