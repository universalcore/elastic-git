import argparse
import os
import sys
from ConfigParser import ConfigParser

from elasticgit import EG
from elasticgit.commands.base import (
    ToolCommand, CommandArgument, ToolCommandError)
from elasticgit.commands.utils import load_models


class ResyncTool(ToolCommand):

    command_name = 'resync'
    command_help_text = ('Tools for resyncing data in a git repository '
                         'with what is in the search index.')
    command_arguments = (
        CommandArgument(
            '-c', '--config',
            dest='config_file',
            help='Python paste config file.', required=True,
            type=argparse.FileType('r')),
        CommandArgument(
            '-m', '--models',
            dest='models_module',
            help='The models module to load.', required=True),
    )

    stdout = sys.stdout

    def run(self, config_file, models_module):
        # NOTE: ConfigParser's DEFAULT handling is kind of nuts
        config = ConfigParser()
        config.set('DEFAULT', 'here', os.getcwd())
        config.readfp(config_file)

        required_options = ['es.index_prefix', 'git.path']
        has_options = [
            config.has_option('app:main', option)
            for option in required_options
        ]

        if not all(has_options):
            raise ToolCommandError(
                'Missing some required options. Required options are: %s' % (
                    ', '.join(required_options)))

        working_dir = config.get('app:main', 'git.path')
        index_prefix = config.get('app:main', 'es.index_prefix')
        workspace = EG.workspace(working_dir, index_prefix=index_prefix)
        models = load_models(models_module)
        for name, klass in models.items():
            updated, removed = workspace.sync(klass)
            self.stdout.writelines('%s: %d updated, %d removed.\n' % (
                name, len(updated), len(removed)))
