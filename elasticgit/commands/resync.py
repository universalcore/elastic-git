import argparse
import os
import sys
import json

from ConfigParser import ConfigParser

from elasticgit import EG
from elasticgit.commands.base import (
    ToolCommand, CommandArgument, ToolCommandError)
from elasticgit.commands.utils import ModelClassType
from elasticgit.utils import fqcn


DEFAULT_SECTION = 'app:cmsfrontend'


class ResyncTool(ToolCommand):

    command_name = 'resync'
    command_help_text = ('Tools for resyncing data in a git repository '
                         'with what is in the search index.')
    command_arguments = (
        CommandArgument(
            '-c', '--config',
            dest='config_file',
            help='Python paste config file.',
            type=argparse.FileType('r')),
        CommandArgument(
            '-m', '--model',
            dest='model_class',
            help='The model class to load.', required=True,
            type=ModelClassType()),
        CommandArgument(
            '-s', '--section-name',
            dest='section_name',
            help='The section from where to read the config keys.',
            default=DEFAULT_SECTION),
        CommandArgument(
            '-i', '--index-prefix',
            dest='index_prefix',
            help='The index prefix to use'),
        CommandArgument(
            '-p', '--git-path',
            dest='git_path',
            help='The path to the repository.'),
        CommandArgument(
            '-f', '--mapping-file',
            dest='mapping_file',
            help='The path to a custom mapping file.',
            type=argparse.FileType('r')),
    )

    stdout = sys.stdout

    def run(self, config_file, model_class, index_prefix, git_path,
            mapping_file=None, section_name=DEFAULT_SECTION):

        mapping = (json.load(mapping_file)
                   if mapping_file is not None
                   else None)

        # resync
        if config_file is not None:
            self.resync_with_config_file(config_file, model_class,
                                         section_name, mapping)
        elif index_prefix and git_path:
            self.resync(git_path, index_prefix, model_class, mapping)
        else:
            raise ToolCommandError(
                'Please specify either `--config` or `--index-prefix` and '
                '`--git-path`.')

    def resync_with_config_file(self, config_file, model_class,
                                section_name, mapping=None):
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

        self.resync(working_dir, index_prefix, model_class, mapping)

    def resync(self, working_dir, index_prefix, model_class, mapping=None):
        workspace = EG.workspace(working_dir, index_prefix=index_prefix)

        if mapping is not None:
            workspace.setup_custom_mapping(model_class, mapping)

        updated, removed = workspace.sync(model_class)
        self.stdout.writelines('%s: %d updated, %d removed.\n' % (
            fqcn(model_class), len(updated), len(removed)))
