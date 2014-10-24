import sys
import json

from elasticgit import version_info
from elasticgit.commands.base import ToolCommand, CommandArgument


class VersionTool(ToolCommand):

    command_name = 'version'
    command_help_text = ('Tools for versioning & version checking '
                         'a content repository')
    command_arguments = (
        CommandArgument(
            '-n', '--name',
            help='The name to give this repository', required=True),
        CommandArgument(
            '-l', '--license',
            help='The license the publish this content under.', required=True),
        CommandArgument(
            '-a', '--author',
            help='The author', required=True),
        CommandArgument(
            '-au', '--author-url',
            help='The url where to find more information about the author'),
    )

    stdout = sys.stdout

    def run(self, name, license, author, author_url=None):
        json.dump({
            'name': name,
            'license': license,
            'author': author,
            'author_url': author_url,
            'version_info': version_info,
        }, fp=self.stdout, indent=2)
