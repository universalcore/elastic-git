import json

from StringIO import StringIO
from ConfigParser import ConfigParser

from elasticgit.tests.base import ToolBaseTest, TestPerson
from elasticgit.commands.resync import ResyncTool, DEFAULT_SECTION


class TestResyncTool(ToolBaseTest):

    def setUp(self):
        self.workspace = self.mk_workspace()
        self.repo = self.workspace.repo
        self.sm = self.workspace.sm
        self.im = self.workspace.im

    def recreate_index(self, branch_name):
        self.im.destroy_index(branch_name)
        self.im.create_index(branch_name)
        while not self.im.index_ready(branch_name):
            True
        self.im.refresh_indices(branch_name)

    def resync(self, workspace, model_class, mapping_file=None):
        tool = ResyncTool()
        tool.stdout = StringIO()
        tool.run(None, model_class,
                 workspace.index_prefix, workspace.working_dir,
                 mapping_file)
        return tool.stdout.getvalue()

    def test_resync_empty_index(self):
        person = TestPerson({
            'age': 1,
            'name': 'Name'
        })
        self.workspace.save(person, 'Saving a person.')
        self.workspace.refresh_index()

        self.assertEqual(self.workspace.S(TestPerson).count(), 1)
        branch_name = self.repo.active_branch.name
        self.recreate_index(branch_name)
        self.assertEqual(self.workspace.S(TestPerson).count(), 0)

        output = self.resync(self.workspace, TestPerson)
        self.assertEqual(
            'elasticgit.tests.base.TestPerson: 1 updated, 0 removed.\n',
            output)

    def test_resync_empty_git(self):
        person = TestPerson({
            'age': 1,
            'name': 'Name'
        })
        self.workspace.save(person, 'Saving a person.')
        self.workspace.delete(person, 'Removing said person.')
        self.workspace.refresh_index()
        self.assertEqual(self.workspace.S(TestPerson).count(), 0)

        # Manually add stale data to the index again
        self.workspace.im.index(person)

        self.workspace.refresh_index()
        self.assertEqual(self.workspace.S(TestPerson).count(), 1)
        output = self.resync(self.workspace, TestPerson)
        self.assertEqual(
            'elasticgit.tests.base.TestPerson: 0 updated, 1 removed.\n',
            output)
        self.workspace.refresh_index()
        self.assertEqual(self.workspace.S(TestPerson).count(), 0)

    def test_resync_partial_out_of_sync(self):
        person1 = TestPerson({
            'age': 1,
            'name': 'Name',
        })
        person2 = TestPerson({
            'age': 1,
            'name': 'Name',
        })
        person3 = TestPerson({
            'page': 1,
            'name': 'Name',
        })

        self.workspace.save(person1, 'Saving a person.')
        self.workspace.save(person2, 'Saving a person.')
        self.workspace.save(person3, 'Saving a person.')

        # manually unindex
        self.workspace.im.unindex(person2)
        self.workspace.im.unindex(person3)
        self.workspace.refresh_index()

        self.assertEqual(self.workspace.S(TestPerson).count(), 1)
        output = self.resync(self.workspace, TestPerson)
        self.assertEqual(
            'elasticgit.tests.base.TestPerson: 3 updated, 0 removed.\n',
            output)
        self.workspace.refresh_index()
        self.assertEqual(self.workspace.S(TestPerson).count(), 3)

    def test_mapping(self):
        mapping = {
            'properties': {
                'uuid': {
                    'type': 'string',
                    'index': 'not_analyzed',
                },
                'name': {
                    'type': 'string',
                    'index': 'not_analyzed',
                },
                'age': {
                    'type': 'integer',
                },
            }
        }
        mapping_file = StringIO()
        json.dump(mapping, fp=mapping_file)
        mapping_file.seek(0)
        self.resync(self.workspace, TestPerson, mapping_file=mapping_file)
        self.assertEqual(
            self.workspace.get_mapping(TestPerson), mapping)


class TestResyncToolWithConfigFile(TestResyncTool):

    def resync(self, workspace, models_module, mapping_file=None):
        parser = ConfigParser()
        parser.add_section(DEFAULT_SECTION)
        parser.set(DEFAULT_SECTION, 'git.path',
                   workspace.working_dir)
        parser.set(DEFAULT_SECTION, 'es.index_prefix',
                   workspace.index_prefix)
        sio = StringIO()
        parser.write(sio)
        sio.seek(0)

        tool = ResyncTool()
        tool.stdout = StringIO()
        tool.run(sio, models_module, None, None, mapping_file)
        return tool.stdout.getvalue()
