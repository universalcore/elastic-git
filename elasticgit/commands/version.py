import sys
import json

from elasticgit.models import version_info
from elasticgit.commands.base import ToolCommand, CommandArgument


DEFAULT_FILE_NAME = '.unicore.json'


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
        CommandArgument(
            '-f', '--file',
            dest='file_name',
            help='The file to write to. Set to `-` for stdout.',
            default=DEFAULT_FILE_NAME)
    )

    opener = open
    stdout = sys.stdout

    def run(self, name, license, author, author_url=None,
            file_name=DEFAULT_FILE_NAME):

        if file_name == '-':
            fp = self.stdout
        else:
            fp = self.opener(file_name, 'w')

        json.dump({
            'name': name,
            'license': license,
            'author': author,
            'author_url': author_url,
            'version_info': version_info,
        }, fp=fp, indent=2)
