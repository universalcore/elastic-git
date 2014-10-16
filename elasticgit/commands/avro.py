from jinja2 import Environment, PackageLoader
import imp
import json
import pprint

from datetime import datetime

from elasticgit.models import (
    Model, IntegerField, TextField, ModelVersionField, FloatField,
    BooleanField, ListField, DictField, UUIDField)

from elasticgit.commands.base import ToolCommand, ToolCommandError


def deserialize(schema, module_name=None):
    """
    Deserialize an Avro schema and define it within a module (if specified)

    :param dict schema:
        The Avro schema
    :param str module_name:
        The name of the module to put this in. This module is dynamically
        generated with :py:func:`imp.new_module` and only available
        during code generation for setting the class' ``__module__``.
    :returns:
        :py:class:`elasticgit.models.Model`

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
    """
    schema_dumper = SchemaDumper()
    return schema_dumper.dump_schema(model_class)


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
        ('schema_file', 'path to Avro schema file.'),
    )

    mapping = {
        'int': IntegerField,
        'string': TextField,
        'float': FloatField,
        'boolean': BooleanField,
        'array': ListField,
        'record': DictField,
    }

    def __init__(self):
        self.env = Environment(loader=PackageLoader('elasticgit', 'templates'))
        self.env.globals['field_class_for'] = self.field_class_for
        self.env.globals['default_value'] = self.default_value

    def field_class_for(self, field):
        field_type = field['type']
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

    def run(self, schema_file):
        """
        Inspect an Avro schema file and write the generated Python code
        to ``self.stdout``

        :param str schema_file:
            The path to the schema file to load.
        """
        with open(schema_file, 'r') as fp:
            schema = json.load(fp)
        self.stdout.write(self.generate_model(schema))

    def generate_model(self, schema):
        """
        Generate Python code for the given Avro schema

        :param dict schema:
            The Avro schema
        :returns: str
        """
        template = self.env.get_template('model_generator.py.txt')
        return template.render(
            datetime=datetime.utcnow(),
            schema=schema)


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
        ('class_path', 'python path to Class.'),
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
