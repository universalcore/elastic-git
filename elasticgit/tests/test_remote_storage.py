from elasticgit.tests.base import ModelBaseTest
from elasticgit.istorage import IStorageManager
from elasticgit.remote_storage import RemoteStorageManager
from elasticgit.tests.base import TestPerson
from elasticgit.utils import fqcn

from requests.models import Response

from mock import patch


class TestRemoteStorage(ModelBaseTest):

    def test_interface(self):
        rsm = RemoteStorageManager('http://www.example.org/repos/foo.json')
        self.assertTrue(IStorageManager.implementedBy(RemoteStorageManager))
        self.assertTrue(IStorageManager.providedBy(rsm))

    def test_url(self):
        class_name = fqcn(TestPerson)
        rsm = RemoteStorageManager('http://www.example.org/repos/foo.json')
        self.assertEqual(
            rsm.url(class_name),
            'http://www.example.org/repos/foo/%s.json' % (class_name,))

    def test_storage_exists(self):
        rsm = RemoteStorageManager('http://www.example.org/repos/foo.json')
        with patch.object(rsm, 'mk_request') as mock:
            response = Response()
            response.status_code = 200
            mock.return_value = response
            self.assertTrue(rsm.storage_exists())

    def test_storage_doesnot_exist(self):
        rsm = RemoteStorageManager('http://www.example.org/repos/foo.json')
        with patch.object(rsm, 'mk_request') as mock:
            response = Response()
            response.status_code = 404
            mock.return_value = response
            self.assertFalse(rsm.storage_exists())
