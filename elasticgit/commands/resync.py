import argparse
import os
import sys
import json

from ConfigParser import ConfigParser

from elasticgit import EG
from elasticgit.commands.base import (
    ToolCommand, CommandArgument, ToolCommandError)
from elasticgit.commands.utils import ModelClassType, BooleanType
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
        CommandArgument(
            '-r', '--recreate-index',
            dest='recreate_index',
            help='Whether or not to recreate the index from scratch.',
            type=BooleanType(), default=False),
    )

    stdout = sys.stdout

    def run(self, config_file, model_class, index_prefix, git_path,
            mapping_file=None, recreate_index=False,
            section_name=DEFAULT_SECTION):

        mapping = (json.load(mapping_file)
                   if mapping_file is not None
                   else None)

        # resync
        if config_file is not None:
            index_prefix, git_path = self.read_config_file(
                config_file, section_name)

        if not all([index_prefix, git_path]):
            raise ToolCommandError(
                'Please specify either `--config` or `--index-prefix` and '
                '`--git-path`.')

        return self.resync(git_path, index_prefix, model_class,
                           mapping=mapping, recreate_index=recreate_index)

    def read_config_file(self, config_file, section_name):
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
        return index_prefix, working_dir

    def resync(self, working_dir, index_prefix, model_class,
               mapping=None, recreate_index=False):

        workspace = EG.workspace(working_dir, index_prefix=index_prefix)
        branch = workspace.sm.repo.active_branch

        if recreate_index and workspace.im.index_exists(branch.name):
            self.stdout.writelines(
                'Destroying index for %s.\n' % (branch.name,))
            workspace.im.destroy_index(branch.name)

        if not workspace.im.index_exists(branch.name):
            self.stdout.writelines(
                'Creating index for %s.\n' % (branch.name,))
            # create the index and wait for it to become ready
            workspace.im.create_index(branch.name)
            while not workspace.index_ready():
                pass

        if mapping is not None:
            self.stdout.writelines(
                'Creating mapping for %s.\n' % (fqcn(model_class),))
            workspace.setup_custom_mapping(model_class, mapping)

        updated, removed = workspace.sync(model_class)
        self.stdout.writelines('%s: %d updated, %d removed.\n' % (
            fqcn(model_class), len(updated), len(removed)))
