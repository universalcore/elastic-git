from elasticgit.tests.base import ModelBaseTest, TestPerson
from elasticgit.manager import StorageException

from git import Repo, GitCommandError


class TestStorage(ModelBaseTest):

    def setUp(self):
        self.workspace = self.mk_workspace()
        self.sm = self.workspace.sm

    def test_storage_exists(self):
        self.workspace.destroy()
        self.assertFalse(self.sm.storage_exists())

    def test_create_storage(self):
        self.sm.create_storage()
        self.assertTrue(self.sm.storage_exists())

    def test_destroy_storage(self):
        self.sm.create_storage()
        self.assertTrue(self.sm.storage_exists())
        self.sm.destroy_storage()
        self.assertFalse(self.sm.storage_exists())

    def test_store(self):
        self.workspace.setup('Test Kees', 'kees@example.org')
        p = TestPerson({
            'age': 1,
            'name': 'Test Kees'
        })
        self.sm.store(p, 'Saving a person.')

    def test_store_readonly(self):
        self.workspace.setup('Test Kees', 'kees@example.org')
        p = TestPerson({
            'age': 1,
            'name': 'Test Kees'
        })
        new_p = p.update({'name': 'Foo'})
        self.assertRaises(
            StorageException, self.sm.store, p, 'Crashing a person.')
        self.assertTrue(self.sm.store(new_p, 'Saving a person.'))

    def test_delete(self):
        self.workspace.setup('Test Kees', 'kees@example.org')
        p = TestPerson({
            'age': 1,
            'name': 'Test Kees'
        })

        self.sm.store(p, 'Saving a person.')
        self.sm.delete(p, 'Deleting a person.')
        repo = Repo(self.workspace.repo.working_dir)
        delete_person, save_person = repo.iter_commits('master')
        self.assertEqual(save_person.message, 'Saving a person.')
        self.assertEqual(save_person.author.name, 'Test Kees')
        self.assertEqual(save_person.author.email, 'kees@example.org')
        self.assertEqual(delete_person.message, 'Deleting a person.')
        self.assertEqual(delete_person.author.name, 'Test Kees')
        self.assertEqual(delete_person.author.email, 'kees@example.org')

    def test_delete_non_existent(self):
        self.workspace.setup('Test Kees', 'kees@example.org')

        person = TestPerson({
            'age': 1,
            'name': 'Test Kees'
        })

        self.assertRaises(
            GitCommandError,
            self.sm.delete, person, 'Deleting a person.')

    def test_get(self):
        self.workspace.setup('Test Kees', 'kees@example.org')
        person = TestPerson({
            'age': 1,
            'name': 'Test Kees',
        })
        self.sm.store(person, 'Saving a person.')
        self.assertEqual(
            self.sm.get(person.__class__, person.uuid), person)

    def test_get_non_existent(self):
        self.workspace.setup('Test Kees', 'kees@example.org')
        person = TestPerson({
            'age': 1,
            'name': 'Test Kees'
        })

        self.assertRaises(
            GitCommandError,
            self.sm.get, person.__class__, person.uuid)

    def test_iterate(self):
        self.workspace.setup('Test Kees', 'kees@example.org')

        person1 = TestPerson({
            'age': 1,
            'name': 'Test Kees 1'
        })
        person2 = TestPerson({
            'age': 2,
            'name': 'Test Kees 2'
        })

        self.sm.store(person1, 'Saving person 1')
        self.sm.store(person2, 'Saving person 2')
        reloaded_person1, reloaded_person2 = self.sm.iterate(TestPerson)
        self.assertEqual(
            set([reloaded_person1.uuid, reloaded_person2.uuid]),
            set([person1.uuid, person2.uuid]))

    def test_load(self):
        self.workspace.setup('Test Kees', 'kees@example.org')
        person = TestPerson({
            'age': 1,
            'name': 'Test Kees',
        })
        self.sm.store(person, 'Saving a person')
        reloaded_person = self.sm.load(
            self.sm.git_path(
                person.__class__, '%s.json' % (person.uuid,)))
        self.assertEqual(person, reloaded_person)
