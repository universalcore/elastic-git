from elasticgit.tests.base import ModelBaseTest
from elasticgit.istorage import IStorageManager
from elasticgit.remote_storage import (
    RemoteStorageManager, RemoteStorageException)
from elasticgit.tests.base import TestPerson
from elasticgit.utils import fqcn

from requests.models import Response

from mock import patch


class TestRemoteStorage(ModelBaseTest):

    def setUp(self):
        self.rsm = RemoteStorageManager(
            'http://www.example.org/repos/foo.json')

    def test_interface(self):
        self.assertTrue(IStorageManager.implementedBy(RemoteStorageManager))
        self.assertTrue(IStorageManager.providedBy(self.rsm))

    def test_url(self):
        class_name = fqcn(TestPerson)
        self.assertEqual(
            self.rsm.url(class_name),
            'http://www.example.org/repos/foo/%s.json' % (class_name,))

    def test_storage_exists(self):
        with patch.object(self.rsm, 'mk_request') as mock:
            response = Response()
            response.status_code = 200
            mock.return_value = response
            self.assertTrue(self.rsm.storage_exists())
            mock.assert_called_with(
                'GET', 'http://www.example.org/repos/foo.json')

    def test_storage_doesnot_exist(self):
        with patch.object(self.rsm, 'mk_request') as mock:
            response = Response()
            response.status_code = 404
            mock.return_value = response
            self.assertFalse(self.rsm.storage_exists())
            mock.assert_called_with(
                'GET', 'http://www.example.org/repos/foo.json')

    def test_write_config(self):
        self.assertRaises(
            RemoteStorageException, self.rsm.write_config, 'foo', {})

    def test_read_config(self):
        self.assertRaises(
            RemoteStorageException, self.rsm.read_config, 'foo')

    def test_destroy_storage(self):
        self.assertRaises(
            RemoteStorageException, self.rsm.destroy_storage)
