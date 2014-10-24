import argparse
import os
import sys
from ConfigParser import ConfigParser

from elasticgit import EG
from elasticgit.commands.base import (
    ToolCommand, CommandArgument, ToolCommandError)
from elasticgit.utils import load_class


DEFAULT_SECTION = 'app:cmsfrontend'


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
            '-m', '--model',
            dest='model_class_name',
            help='The model class to load.', required=True),
        CommandArgument(
            '-s', '--section-name',
            dest='section_name',
            help='The section from where to read the config keys.',
            default=DEFAULT_SECTION)
    )

    stdout = sys.stdout

    def run(self, config_file, model_class_name, section_name=DEFAULT_SECTION):
        # NOTE: ConfigParser's DEFAULT handling is kind of nuts
        config = ConfigParser()
        config.set('DEFAULT', 'here', os.getcwd())
        config.readfp(config_file)

        required_options = ['es.index_prefix', 'git.path']
        has_options = [
            config.has_option(section_name, option)
            for option in required_options
        ]

        if not all(has_options):
            raise ToolCommandError(
                'Missing some required options. Required options are: %s' % (
                    ', '.join(required_options)))

        working_dir = config.get(section_name, 'git.path')
        index_prefix = config.get(section_name, 'es.index_prefix')
        workspace = EG.workspace(working_dir, index_prefix=index_prefix)
        model = load_class(model_class_name)
        updated, removed = workspace.sync(model)
        self.stdout.writelines('%s: %d updated, %d removed.\n' % (
            model_class_name, len(updated), len(removed)))
