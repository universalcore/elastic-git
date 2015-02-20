# -*- coding: utf-8 -*-

import os
import shutil

from elasticgit.tests.base import ModelBaseTest, TestPerson
from elasticgit import EG
from elasticgit.storage import StorageException, StorageManager

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
        p = TestPerson({
            'age': 1,
            'name': 'Test Kees'
        })
        self.sm.store(p, 'Saving a person.')

    def test_store_unicode_commit_message(self):
        p = TestPerson({
            'age': 1,
            'name': 'Test Kees'
        })
        message = u'Saving a përsøn.'
        self.assertRaises(
            StorageException, self.sm.store, p, message)

    def test_store_readonly(self):
        p = TestPerson({
            'age': 1,
            'name': 'Test Kees'
        })
        new_p = p.update({'name': 'Foo'})
        self.assertRaises(
            StorageException, self.sm.store, p, 'Crashing a person.')
        self.assertTrue(self.sm.store(new_p, 'Saving a person.'))

    def test_delete(self):
        p = TestPerson({
            'age': 1,
            'name': 'Test Kees'
        })

        self.sm.store(p, 'Saving a person.')
        self.sm.delete(p, 'Deleting a person.',
                       author=('Foo Bar', 'foo@example.org'),
                       committer=('Bar Foo', 'bar@example.org'))
        repo = Repo(self.workspace.repo.working_dir)
        delete_person, save_person, _ = repo.iter_commits('master')
        self.assertEqual(save_person.message, 'Saving a person.')
        self.assertEqual(save_person.author.name, 'Test Kees')
        self.assertEqual(save_person.author.email, 'kees@example.org')
        self.assertEqual(delete_person.message, 'Deleting a person.')
        self.assertEqual(delete_person.author.name, 'Foo Bar')
        self.assertEqual(delete_person.author.email, 'foo@example.org')
        self.assertEqual(delete_person.committer.name, 'Bar Foo')
        self.assertEqual(delete_person.committer.email, 'bar@example.org')

    def test_delete_non_existent(self):
        person = TestPerson({
            'age': 1,
            'name': 'Test Kees'
        })

        self.assertRaises(
            GitCommandError,
            self.sm.delete, person, 'Deleting a person.')

    def test_get(self):
        person = TestPerson({
            'age': 1,
            'name': 'Test Kees',
        })
        self.sm.store(person, 'Saving a person.')
        self.assertEqual(
            self.sm.get(person.__class__, person.uuid), person)

    def test_get_non_existent(self):
        person = TestPerson({
            'age': 1,
            'name': 'Test Kees'
        })

        self.assertRaises(
            GitCommandError,
            self.sm.get, person.__class__, person.uuid)

    def test_iterate(self):
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
        person = TestPerson({
            'age': 1,
            'name': 'Test Kees',
        })
        self.sm.store(person, 'Saving a person')
        reloaded_person = self.sm.load(
            self.sm.git_path(
                person.__class__, '%s.json' % (person.uuid,)))
        self.assertEqual(person, reloaded_person)

    def test_clone_from(self):
        workspace = self.workspace
        person = TestPerson({
            'age': 1,
            'name': 'Test Kees 1'
        })
        workspace.save(person, 'Saving a person')

        clone_source = workspace.working_dir
        clone_dest = '%s_clone' % (workspace.working_dir,)
        cloned_repo = EG.clone_repo(clone_source, clone_dest)
        workspace = EG.workspace(cloned_repo.working_dir)
        self.addCleanup(workspace.destroy)

        sm = StorageManager(cloned_repo)
        [cloned_person] = sm.iterate(TestPerson)
        self.assertEqual(person, cloned_person)

    def test_clone_from_bare_repository(self):
        bare_repo_name = '%s_bare' % (self.id(),)
        bare_repo_path = os.path.join(self.WORKING_DIR, bare_repo_name)
        bare_repo = EG.init_repo(bare_repo_path, bare=True)
        self.assertEqual(bare_repo.bare, True)

        if self.destroy:
            self.addCleanup(lambda: shutil.rmtree(bare_repo_path))

        cloned_repo_path = '%s_clone' % (bare_repo_path,)
        EG.clone_repo(bare_repo_path, cloned_repo_path)
        new_workspace = EG.workspace(cloned_repo_path)
        if self.destroy:
            self.addCleanup(new_workspace.destroy)

        # create an initial commit
        initial_commit = new_workspace.sm.store_data(
            'README.md', '# Hello World', 'Initial commit')

        repo = new_workspace.repo
        # NOTE: this is a bare remote repo and so it doesn't have a working
        #       copy checked out, there's nothing on the remote.
        [origin] = repo.remotes
        origin.push('refs/heads/master:refs/heads/master')

        # Now pull in the changes in a remote repo to ensure we've
        # succesfully are able to push & pull things around
        second_cloned_repo_path = '%s_second_clone' % (bare_repo_path,)
        EG.clone_repo(bare_repo_path, second_cloned_repo_path)
        second_workspace = EG.workspace(second_cloned_repo_path)
        second_workspace.fast_forward()
        self.addCleanup(second_workspace.destroy)

        [found_commit] = second_workspace.repo.iter_commits()
        self.assertEqual(found_commit, initial_commit)

    def test_delete_data(self):
        storage = self.workspace.sm
        readme_path = os.path.join(self.workspace.repo.working_dir,
                                   'README.md')
        readme_commit = storage.store_data(
            'README.md', '# Hello World', 'Read me commit')
        self.assertTrue(os.path.isfile(readme_path))
        delete_commit = storage.delete_data('README.md', 'Delete the readme')
        self.assertFalse(os.path.isfile(readme_path))
