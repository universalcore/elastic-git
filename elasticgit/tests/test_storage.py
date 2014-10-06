from elasticgit.tests.base import ModelBaseTest


class TestStorage(ModelBaseTest):

    def setUp(self):
        self.workspace = self.mk_workspace()
        self.sm = self.workspace.sm

    def tearDown(self):
        if self.workspace.exists():
            self.workspace.destroy()

    def test_exists(self):
        self.assertFalse(self.sm.storage_exists())

    def test_create(self):
        self.sm.create_storage('Test Kees', 'kees@example.org')
        self.assertTrue(self.sm.storage_exists())

    def test_destroy(self):
        self.sm.create_storage('Test Kees', 'kees@example.org')
        self.assertTrue(self.sm.storage_exists())
        self.sm.destroy_storage()
        self.assertFalse(self.sm.storage_exists())
