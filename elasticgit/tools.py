import argparse
import sys
import json

from elasticgit.models import (
    Model, IntegerField, TextField, ModelVersionField, FloatField,
    BooleanField, ListField)


class ArgumentParserError(Exception):
    pass


class SchemaDumper(object):

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
        }
        if field.default:
            data['default'] = field.default
        if field.fallbacks:
            data['aliases'] = [
                fallback.field_name for fallback in field.fallbacks]
        return data


def get_parser():
    parser = argparse.ArgumentParser(
        description="Elasticgit command line tools.")
    subparsers = parser.add_subparsers(help='Commands')
    dump_schema = subparsers.add_parser(
        'dump_schema', help='Dump model schema information.')
    dump_schema.add_argument(
        'class_path', help='python path to Class')
    dump_schema.set_defaults(dispatcher=SchemaDumper)
    return parser


if __name__ == '__main__':
    parser = get_parser()
    args = parser.parse_args()
    data = vars(args)
    dispatcher_class = data.pop('dispatcher')
    dispatcher = dispatcher_class()
    dispatcher.run(**data)
