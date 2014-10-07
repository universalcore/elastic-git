from elasticgit.tests.base import ModelBaseTest, TestPerson
from elasticgit.manager import ModelMappingType
from git import Repo


class TestWorkspace(ModelBaseTest):

    def setUp(self):
        self.workspace = self.mk_workspace()

    def tearDown(self):
        if self.workspace.exists():
            self.workspace.destroy()

    def test_exists(self):
        self.assertFalse(self.workspace.exists())

    def test_storage_exists(self):
        self.workspace.setup('Test Kees', 'kees@example.org')
        self.workspace.im.destroy_index()
        self.assertTrue(self.workspace.exists())

    def test_index_exists(self):
        self.workspace.setup('Test Kees', 'kees@example.org')
        self.workspace.sm.destroy_storage()
        self.assertTrue(self.workspace.exists())

    def test_setup(self):
        self.workspace.setup('Test Kees', 'kees@example.org')
        self.assertTrue(self.workspace.sm.storage_exists())
        self.assertTrue(self.workspace.im.index_exists())
        self.assertTrue(self.workspace.exists())

        repo = Repo(self.workspace.workdir)
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

    def tearDown(self):
        if self.workspace.exists():
            self.workspace.destroy()

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
            'name': 'Name'
        })

        workspace.save(person, 'Saving a person')
        workspace.refresh_index()
        [result] = workspace.S(TestPerson).query(name__match='Name')
        self.assertTrue(isinstance(result, ModelMappingType))
        model = result.get_object()
        self.assertTrue(isinstance(model, TestPerson))
        self.assertEqual(model, person)
