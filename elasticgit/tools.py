import argparse
from jinja2 import Environment, PackageLoader
import json
import sys
import pprint

from datetime import datetime

from elasticgit.models import (
    Model, IntegerField, TextField, ModelVersionField, FloatField,
    BooleanField, ListField, DictField, UUIDField)


class ArgumentParserError(Exception):
    pass


class SchemaLoader(object):
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

    #: Where the write the output to, override for testing.
    stdout = sys.stdout
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
        template = self.env.get_template('model_generator.jinja2')
        return template.render(
            datetime=datetime.utcnow(),
            schema=schema)


class SchemaDumper(object):
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

    #: Where the write the output to, override for testing.
    stdout = sys.stdout

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
            raise ArgumentParserError(
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


def add_command(subparsers, dispatcher_class):  # pragma: no cover
    command = subparsers.add_parser(
        dispatcher_class.command_name,
        help=dispatcher_class.command_help_text)
    for argument, argument_help in dispatcher_class.command_arguments:
        command.add_argument(argument, help=argument_help)
    command.set_defaults(dispatcher=dispatcher_class)


def get_parser():  # pragma: no cover
    parser = argparse.ArgumentParser(
        description="Elasticgit command line tools.")
    subparsers = parser.add_subparsers(help='Commands')

    add_command(subparsers, SchemaDumper)
    add_command(subparsers, SchemaLoader)

    return parser


if __name__ == '__main__':  # pragma: no cover
    parser = get_parser()
    args = parser.parse_args()
    data = vars(args)
    dispatcher_class = data.pop('dispatcher')
    dispatcher = dispatcher_class()
    dispatcher.run(**data)
