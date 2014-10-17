import types
import os

from elasticgit.tests.base import ModelBaseTest, TestPerson, TestPage
from elasticgit.manager import ModelMappingType
from elasticgit.utils import introspect_properties

from git import Repo, GitCommandError


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

    def is_file(self, workspace, model, suffix):
        return os.path.isfile(
            os.path.join(
                workspace.working_dir,
                model.__module__,
                model.__class__.__name__,
                '%s.%s' % (model.uuid, suffix)))

    def assertDataFile(self, workspace, model, suffix='json'):
        self.assertTrue(
            self.is_file(workspace, model, suffix),
            '%s has no data file.' % (model,))

    def assertNotDataFile(self, workspace, model, suffix='json'):
        self.assertFalse(
            self.is_file(workspace, model, suffix),
            '%s has a data file.' % (model,))

    def test_deleting(self):
        workspace = self.workspace
        person = TestPerson({
            'age': 1,
            'name': 'Name'
        })

        workspace.save(person, 'Saving a person')
        self.assertDataFile(workspace, person)

        workspace.refresh_index()
        self.assertEqual(
            workspace.S(TestPerson).query(name__match='Name').count(), 1)
        git_person = workspace.sm.get(TestPerson, person.uuid)
        self.assertEqual(git_person, person)

        workspace.delete(person, 'Deleting a person')
        self.assertNotDataFile(workspace, person)

        workspace.refresh_index()
        self.assertEqual(
            workspace.S(TestPerson).query(name__match='Name').count(), 0)
        self.assertRaises(
            GitCommandError, workspace.sm.get, TestPerson, person.uuid)

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

    def test_reindex_iter(self):
        workspace = self.workspace
        person = TestPerson({
            'age': 1,
            'name': 'Name'
        })
        workspace.save(person, 'Saving a person')

        iterator = workspace.reindex_iter(TestPerson)
        self.assertTrue(iterator, types.GeneratorType)
        [reindexed] = list(iterator)
        self.assertEqual(person, reindexed)

    def test_reindex(self):
        workspace = self.workspace
        repo = workspace.repo
        person = TestPerson({
            'age': 1,
            'name': 'Name'
        })
        workspace.save(person, 'Saving a person')
        workspace.im.destroy_index(repo.active_branch.name)
        workspace.im.create_index(repo.active_branch.name)

        while not workspace.index_ready():
            pass

        workspace.refresh_index()
        self.assertEqual(
            workspace.S(TestPerson).count(), 0)
        [reindexed] = workspace.reindex(TestPerson)
        self.assertEqual(reindexed.uuid, person.uuid)
        self.assertEqual(
            workspace.S(TestPerson).count(), 1)

    def test_case_sensitivity(self):
        workspace = self.workspace
        page = TestPage({
            'title': 'Sample title',
            'slug': 'sample-title',
            'language': 'eng_UK'
        })
        workspace.save(page, 'Saving a page')

        page2 = TestPage({
            'title': 'Sample title 2',
            'slug': 'sample-title-2',
            'language': 'eng_UK'
        })
        workspace.save(page2, 'Saving a page 2')

        page3 = TestPage({
            'title': 'Sample title 3',
            'slug': 'sample-title-3',
            'language': 'swh_TZ'
        })
        workspace.save(page3, 'Saving a page 3')

        workspace.refresh_index()
        self.assertEqual(
            workspace.S(TestPage).query(language__match='eng_UK').count(), 2)

        self.assertEqual(
            workspace.S(TestPage).query(
                slug__match_phrase='sample-title').count(), 3)

        # this currently matches all 3 pages
        self.assertEqual(
            workspace.S(TestPage).query(
                slug__match_phrase='sample-title-3').count(), 1)
