import os
import glob
import json
import warnings
from contextlib import contextmanager

from elasticgit.commands.base import ToolCommand
from elasticgit.commands import avro
from elasticgit.manager import StorageManager

from git import Repo


class NotAGitModelException(Exception):
    pass


class MigrateGitModelRepo(ToolCommand):

    command_name = 'migrate-gitmodel-repo'
    command_help_text = ('Migrate a GitModel based repository layout to an'
                         'Elastic-Git repository layout')
    command_arguments = (
        ('working_dir', 'The directory of git model repository to migrate.'),
        ('module_name', 'The module to put the migrated data in.'),
    )

    default_type = 'string'

    def run(self, working_dir, module_name):
        repo = Repo(working_dir)
        storage_manager = StorageManager(repo)
        records = []
        target_dir = os.path.join(repo.working_dir, module_name)
        gitmodel_info = self.inspect_repo(repo, target_dir)
        for directory, schema, data_records in gitmodel_info:

            # GitModel uses ``id``, ElasticGit uses ``uuid`` so add an alias.
            schema = self.add_alias(schema, 'uuid', 'id')
            # Update the namespace for where we're migrating to.
            schema['namespace'] = module_name

            model_class = avro.deserialize(schema, module_name=module_name)
            for data_record in data_records:
                record = model_class(data_record)
                storage_manager.store(record, 'Migrated %s.' % (
                    record.uuid,))
                records.append(record)

            # Save the schema in the new module's dir
            file_path = os.path.join(target_dir,
                                     '%s.avro.json' % (schema['name'],))
            with self.get_stdout(file_path) as stdout:
                json.dump(schema, fp=stdout, indent=2)

        return schema, records

    def add_alias(self, schema, field_name, alias):
        schema = schema.copy()
        [field] = [field
                   for field in schema['fields']
                   if field['name'] == alias]
        replacement = field.copy()
        replacement['name'] = field_name
        replacement.setdefault('aliases', []).append(alias)
        schema['fields'].append(replacement)
        return schema

    @contextmanager
    def get_stdout(self, file_path):
        fp = open(file_path, 'w')
        yield fp
        fp.close()

    def list_dirs(self, path):
        return [dir_path
                for dir_path in glob.glob(os.path.join(path, '*'))
                if os.path.isdir(dir_path)]

    def inspect_repo(self, repo, target_dir):
        for directory in self.list_dirs(repo.working_dir):

            # Don't inspect the directory we're writing our migrated
            # models to.
            if directory == target_dir:
                continue

            try:
                schema, records = self.inspect_data_dir(directory)
                yield directory, schema, records
            except NotAGitModelException:
                warnings.warn(
                    'Directory %s does not look like a git model.' % (
                        directory,))

    def inspect_data_dir(self, data_dir):
        data_folders = self.list_dirs(data_dir)
        if not data_folders:
            warnings.warn('Directory %s is empty.' % (data_dir,))

        schema = self.guess_initial_schema(data_folders[0])
        records = []
        for data_folder in data_folders:
            data = self.get_data(data_folder)
            schema = self.update_null_types(data, schema)
            records.append(data['fields'])

        null_types = self.get_null_types(schema)
        for field in null_types:
            warnings.warn('Defaulting to %s for null type %s.%s' % (
                self.default_type, schema['name'], field['name'],))
            field['type'] = self.default_type

        return schema, records

    def get_null_types(self, schema):
        return [field for field in schema['fields']
                if field['type'] == 'null']

    def get_data(self, data_folder):
        data_file = os.path.join(data_folder, 'data.json')

        if not os.path.isfile(data_file):
            raise NotAGitModelException()

        with open(data_file, 'r') as fp:
            return json.load(fp)

    def update_null_types(self, data, schema):
        schema = schema.copy()
        for key, value in data['fields'].items():
            guessed_type = self.guess_type(value)
            if guessed_type != 'null':
                for field in schema['fields']:
                    if field['name'] == key:
                        field['type'] = guessed_type
        return schema

    def guess_initial_schema(self, data_folder):
        data = self.get_data(data_folder)
        return {
            'type': 'record',
            'name': data['model'],
            'namespace': data_folder.split('/')[-2],
            'fields': [{
                'name': key,
                'type': self.guess_type(value),
            } for key, value in data['fields'].items()]
        }

    def guess_type(self, value):
        return {
            int: 'int',
            bool: 'boolean',
            float: 'float',
            str: 'string',
            unicode: 'string',
            list: 'array',
            None: 'null',
        }[None if value is None else type(value)]
