import os
import glob
import json
import warnings
from contextlib import contextmanager

from elasticgit.commands.base import ToolCommand

from git import Repo


class MigrateGitModelRepo(ToolCommand):

    command_name = 'migrate-gitmodel-repo'
    command_help_text = ('Migrate a GitModel based repository layout to an'
                         'Elastic-Git repository layout')
    command_arguments = (
        ('working_dir', 'The directory of git model repository to migrate.'),
    )

    def run(self, working_dir):
        self.inspect_repo(Repo(working_dir))

    @contextmanager
    def get_stdout(self, dir):
        fp = open(os.path.join(dir, 'avro.json'), 'w')
        yield fp
        fp.close()

    def list_dirs(self, path):
        return [path
                for path in glob.glob(os.path.join(path, '*'))
                if os.path.isdir(path)]

    def inspect_repo(self, repo):
        for dir in self.list_dirs(repo.working_dir):
            with self.get_stdout(dir) as stdout:
                json.dump(self.inspect_data_dir(dir), fp=stdout, indent=2)

    def inspect_data_dir(self, data_dir):
        data_folders = self.list_dirs(data_dir)
        schema = self.guess_initial_schema(data_folders[0])
        for data_folder in data_folders[1:]:
            schema = self.update_null_types(data_folder, schema)
            if not self.get_null_types(schema):
                break

        null_types = self.get_null_types(schema)
        for field in null_types:
            warnings.warn('Defaulting to null for: %s.%s' % (
                schema['name'], field['name'],))

        return schema

    def get_null_types(self, schema):
        return [field for field in schema['fields']
                if field['type'] == 'null']

    def get_data(self, data_folder):
        data_file = os.path.join(data_folder, 'data.json')
        with open(data_file, 'r') as fp:
            return json.load(fp)

    def update_null_types(self, data_folder, schema):
        schema = schema.copy()
        data = self.get_data(data_folder)
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
