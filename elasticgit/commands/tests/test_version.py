from StringIO import StringIO
import json

from elasticgit import version_info
from elasticgit.tests.base import ToolBaseTest
from elasticgit.commands.version import VersionTool


class TestVersionTool(ToolBaseTest):

    def test_dump_version_info(self):
        tool = VersionTool()
        tool.stdout = StringIO()
        tool.run('the name', 'the license', 'the author', 'the author url')
        self.assertEqual(
            json.loads(tool.stdout.getvalue()),
            {
                'name': 'the name',
                'license': 'the license',
                'author': 'the author',
                'author_url': 'the author url',
                'version_info': version_info
            })
