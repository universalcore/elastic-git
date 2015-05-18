from elasticgit.tests.base import ModelBaseTest
from elasticgit.istorage import IStorageManager
from elasticgit.remote_storage import RemoteStorageManager


class TestRemoteStorage(ModelBaseTest):

    def setUp(self):
        self.rsm = RemoteStorageManager('http://www.example.org')

    def test_interface(self):
        self.assertTrue(IStorageManager.implementedBy(RemoteStorageManager))
        self.assertTrue(IStorageManager.providedBy(self.rsm))
