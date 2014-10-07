from elasticgit.tests.base import ModelBaseTest
from elasticgit.models import IntegerField, TextField


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
        Person = self.mk_model({
            'age': IntegerField('An age'),
            'name': TextField('A name'),
        })

        p = Person({
            'age': 1,
            'name': 'Test Kees',
        })
        self.sm.save(p, 'Saving a person.')
