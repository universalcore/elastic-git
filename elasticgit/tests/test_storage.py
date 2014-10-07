from elasticgit.tests.base import ModelBaseTest
from elasticgit.models import IntegerField, TextField

from git import Repo, GitCommandError


class TestStorage(ModelBaseTest):

    def setUp(self):
        self.workspace = self.mk_workspace()
        self.sm = self.workspace.sm

    def tearDown(self):
        if self.workspace.exists():
            self.workspace.destroy()

    def test_storage_exists(self):
        self.assertFalse(self.sm.storage_exists())

    def test_create_storage(self):
        self.sm.create_storage('Test Kees', 'kees@example.org')
        self.assertTrue(self.sm.storage_exists())

    def test_destroy_storage(self):
        self.sm.create_storage('Test Kees', 'kees@example.org')
        self.assertTrue(self.sm.storage_exists())
        self.sm.destroy_storage()
        self.assertFalse(self.sm.storage_exists())

    def test_save(self):
        self.workspace.setup('Test Kees', 'kees@example.org')
        p = self.mk_instance([
            ('age', IntegerField, 1),
            ('name', TextField, 'Test Kees'),
        ])
        self.sm.save(p, 'Saving a person.')

    def test_delete(self):
        self.workspace.setup('Test Kees', 'kees@example.org')
        p = self.mk_instance([
            ('age', IntegerField, 1),
            ('name', TextField, 'Test Kees'),
        ])

        self.sm.save(p, 'Saving a person.')
        self.sm.delete(p, 'Deleting a person.')
        repo = Repo(self.workspace.workdir)
        delete_person, save_person, init_repo = repo.iter_commits('master')
        self.assertEqual(save_person.message, 'Saving a person.')
        self.assertEqual(save_person.author.name, 'Test Kees')
        self.assertEqual(save_person.author.email, 'kees@example.org')
        self.assertEqual(delete_person.message, 'Deleting a person.')
        self.assertEqual(delete_person.author.name, 'Test Kees')
        self.assertEqual(delete_person.author.email, 'kees@example.org')

    def test_delete_non_existent(self):
        self.workspace.setup('Test Kees', 'kees@example.org')

        person = self.mk_instance([
            ('age', IntegerField, 1),
            ('name', TextField, 'Test Kees'),
        ])

        self.assertRaises(
            GitCommandError,
            self.sm.delete, person, 'Deleting a person.')
