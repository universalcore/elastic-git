from StringIO import StringIO
import json

from elasticgit.models import version_info
from elasticgit.tests.base import ToolBaseTest
from elasticgit.commands.version import VersionTool, DEFAULT_FILE_NAME


class TestVersionTool(ToolBaseTest):

    def test_dump_version_info_stdout(self):
        tool = VersionTool()
        tool.stdout = StringIO()
        tool.run('the name', 'the license', 'the author',
                 author_url='the author url',
                 file_name='-')
        self.assertEqual(
            json.loads(tool.stdout.getvalue()),
            {
                'name': 'the name',
                'license': 'the license',
                'author': 'the author',
                'author_url': 'the author url',
                'version_info': version_info
            })

    def test_dump_version_info(self):

        self.file_name = None
        self.sio = StringIO()

        def patched_open(file_name, mode):
            self.file_name = file_name
            return self.sio

        tool = VersionTool()
        tool.opener = patched_open
        tool.run('the name', 'the license', 'the author',
                 author_url='the author url')
        self.assertEqual(self.file_name, DEFAULT_FILE_NAME)
        self.assertEqual(
            json.loads(self.sio.getvalue()),
            {
                'name': 'the name',
                'license': 'the license',
                'author': 'the author',
                'author_url': 'the author url',
                'version_info': version_info
            })
