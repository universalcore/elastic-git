import argparse
from jinja2 import Environment, PackageLoader, environmentfunction
import json
import pkg_resources
import sys

from datetime import datetime

from elasticgit.models import (
    Model, IntegerField, TextField, ModelVersionField, FloatField,
    BooleanField, ListField)


class ArgumentParserError(Exception):
    pass


class SchemaLoader(object):

    command_name = 'load-schema'
    command_help_text = 'Dump an Avro schema as an Elasticgit model.'
    command_arguments = (
        ('schema_file', 'path to Avro schema file.'),
    )

    stdout = sys.stdout
    mapping = {
        'int': IntegerField,
        'string': TextField,
        'float': FloatField,
        'boolean': BooleanField,
        'array': ListField,
        'record': ModelVersionField,
    }

    def __init__(self):
        self.env = Environment(loader=PackageLoader('elasticgit', 'templates'))
        self.env.globals['field_class_for'] = self.field_class_for
        self.env.globals['default_value'] = self.default_value

    def field_class_for(self, field):
        return self.mapping[field['type']].__name__

    def default_value(self, field):
        return repr(field['default'])

    def run(self, schema_file):
        with open(schema_file, 'r') as fp:
            self.schema = json.load(fp)
        return self.generate_model(self.schema)

    def generate_model(self, schema):
        template = self.env.get_template('model_generator.jinja2')
        return template.render(
            datetime=datetime.utcnow(),
            schema=schema)


class SchemaDumper(object):

    command_name = 'dump-schema'
    command_help_text = 'Dump model information as an Avro schema.'
    command_arguments = (
        ('class_path', 'python path to Class.'),
    )

    stdout = sys.stdout
    mapping = {
        IntegerField: 'int',
        TextField: 'string',
        FloatField: 'float',
        BooleanField: 'boolean',
        ListField: 'array',
        ModelVersionField: {
            'type': 'record',
            'name': 'ModelVersionField',
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
        module_path, name = class_path.rsplit('.', 1)
        parent_module = __import__(module_path, fromlist=[name])
        model_class = getattr(parent_module, name)

        if not issubclass(model_class, Model):
            raise ArgumentParserError(
                '%r is not a subclass of %r' % (model_class, Model))
        return self.dump_schema(model_class)

    def dump_schema(self, model_class):
        json.dump({
            'type': 'record',
            'namespace': model_class.__module__,
            'name': model_class.__name__,
            'fields': [self.get_field_info(name, field)
                       for name, field in model_class._fields.items()],
        }, self.stdout, indent=2)

    def get_field_info(self, name, field):
        data = {
            'name': name,
            'type': self.mapping[field.__class__],
            'doc': field.doc,
        }
        if field.default:
            data['default'] = field.default
        if field.fallbacks:
            data['aliases'] = [
                fallback.field_name for fallback in field.fallbacks]
        return data


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
