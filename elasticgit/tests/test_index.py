from elasticgit.tests.base import ModelBaseTest


class TestIndex(ModelBaseTest):

    def setUp(self):
        self.workspace = self.mk_workspace()
        self.index = self.workspace.index
        self.storage = self.workspace.storage

    def tearDown(self):
        if self.storage.exists():
            self.storage.destroy()

        if self.index.exists():
            self.index.destroy()

    def test_exists(self):
        self.assertFalse(self.index.exists())

    def test_create(self):
        self.index.create()
        self.assertTrue(self.index.exists())

    def test_destroy(self):
        self.index.create()
        self.assertTrue(self.index.exists())
        self.index.destroy()
        self.assertFalse(self.index.exists())
