from elasticgit.tests.base import ModelBaseTest


class TestWorkspace(ModelBaseTest):

    def setUp(self):
        self.workspace = self.mk_workspace()

    def tearDown(self):
        if self.workspace.exists():
            self.workspace.destroy()

    def test_exists(self):
        self.assertFalse(self.workspace.exists())

    def test_storage_exists(self):
        self.workspace.setup()
        self.workspace.im.destroy_index()
        self.assertTrue(self.workspace.exists())

    def test_index_exists(self):
        self.workspace.setup()
        self.workspace.sm.destroy_storage()
        self.assertTrue(self.workspace.exists())

    def test_setup(self):
        self.workspace.setup()
        self.assertTrue(self.workspace.sm.storage_exists())
        self.assertTrue(self.workspace.im.index_exists())
        self.assertTrue(self.workspace.exists())

    def test_destroy(self):
        self.workspace.setup()
        self.assertTrue(self.workspace.exists())
        self.workspace.destroy()
        self.assertFalse(self.workspace.exists())
