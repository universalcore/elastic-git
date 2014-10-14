from elasticgit.tests.base import ModelBaseTest, TestPerson
from elasticgit.manager import ModelMappingType

from git import Repo


class TestWorkspace(ModelBaseTest):

    def setUp(self):
        self.workspace = self.mk_workspace()

    def test_exists(self):
        self.assertFalse(self.workspace.exists())

    def test_storage_exists(self):
        self.workspace.setup('Test Kees', 'kees@example.org')
        repo = self.workspace.repo
        self.workspace.im.destroy_index(repo.active_branch.name)
        self.assertTrue(self.workspace.sm.storage_exists())
        self.assertFalse(self.workspace.exists())

    def test_index_exists(self):
        self.workspace.setup('Test Kees', 'kees@example.org')
        repo = self.workspace.sm.repo
        branch = repo.active_branch
        self.workspace.sm.destroy_storage()
        self.assertTrue(self.workspace.im.index_exists(branch.name))

    def test_setup(self):
        self.workspace.setup('Test Kees', 'kees@example.org')
        self.assertTrue(self.workspace.sm.storage_exists())
        repo = self.workspace.sm.repo
        branch = repo.active_branch
        self.assertTrue(self.workspace.im.index_exists(branch.name))
        self.assertTrue(self.workspace.exists())

        repo = Repo(repo.working_dir)
        config = repo.config_reader()
        self.assertEqual(
            config.get_value('user', 'name'), 'Test Kees')
        self.assertEqual(
            config.get_value('user', 'email'), 'kees@example.org')

    def test_destroy(self):
        self.workspace.setup('Test Kees', 'kees@example.org')
        self.assertTrue(self.workspace.exists())
        self.workspace.destroy()
        self.assertFalse(self.workspace.exists())


class TestEG(ModelBaseTest):

    def setUp(self):
        self.workspace = self.mk_workspace()
        self.workspace.setup('Test Kees', 'kees@example.org')

    def test_saving(self):
        workspace = self.workspace
        person = TestPerson({
            'age': 1,
            'name': 'Name'
        })

        workspace.save(person, 'Saving a person')
        workspace.refresh_index()
        self.assertEqual(
            workspace.S(TestPerson).query(name__match='Name').count(), 1)

    def test_get_object(self):
        workspace = self.workspace
        person = TestPerson({
            'age': 1,
            'name': u'Name',
            'uuid': u'foo',
        })

        workspace.save(person, 'Saving a person')
        workspace.refresh_index()
        [result] = workspace.S(TestPerson).query(name__match='Name')
        self.assertTrue(isinstance(result, ModelMappingType))
        model = result.get_object()
        self.assertTrue(isinstance(model, TestPerson))
        self.assertEqual(model, person)

    def test_access_elastic_search_data(self):
        workspace = self.workspace
        person = TestPerson({
            'age': 1,
            'name': 'Name'
        })
        workspace.save(person, 'Saving a person')
        workspace.refresh_index()
        [result] = workspace.S(TestPerson).query(name__match='Name')
        self.assertTrue(isinstance(result, ModelMappingType))
        self.assertEqual(result.age, 1)
        self.assertEqual(result.name, 'Name')

    def test_getting_back_same_uuids(self):
        workspace = self.workspace
        person = TestPerson({
            'age': 1,
            'name': 'Name'
        })

        workspace.save(person, 'Saving a person')
        workspace.refresh_index()
        [es_person] = workspace.S(TestPerson).query(name__match='Name')
        git_person = es_person.get_object()
        self.assertTrue(
            person.uuid == es_person.uuid == git_person.uuid)
        self.assertEqual(dict(person), dict(git_person))
