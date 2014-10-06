from elasticgit.tests.base import ModelBaseTest


class TestIndex(ModelBaseTest):

    def setUp(self):
        self.workspace = self.mk_workspace()
        self.im = self.workspace.im

    def tearDown(self):
        if self.workspace.exists():
            self.workspace.destroy()

    def test_exists(self):
        self.assertFalse(self.im.index_exists())

    def test_create(self):
        self.im.create_index()
        self.assertTrue(self.im.index_exists())

    def test_destroy(self):
        self.im.create_index()
        self.assertTrue(self.im.index_exists())
        self.im.destroy_index()
        self.assertFalse(self.im.index_exists())
