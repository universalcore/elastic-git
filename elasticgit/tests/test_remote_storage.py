import json

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

    def test_store(self):
        self.assertRaises(
            RemoteStorageException, self.rsm.store, TestPerson({}),
            'commit message')

    def test_store_data(self):
        self.assertRaises(
            RemoteStorageException, self.rsm.store_data, 'foo/bar',
            'data', 'commit message')

    def test_delete(self):
        self.assertRaises(
            RemoteStorageException, self.rsm.delete, TestPerson({}),
            'commit message')

    def test_delete_data(self):
        self.assertRaises(
            RemoteStorageException, self.rsm.delete_data, 'foo/bar',
            'commit message')

    def test_iterate(self):
        with patch.object(self.rsm, 'mk_request') as mock:
            response = Response()
            response.encoding = 'utf-8'
            response._content = json.dumps([{
                'uuid': 'person1',
                'age': 1,
                'name': 'person1'
            }, {
                'uuid': 'person2',
                'age': 2,
                'name': 'person2'
            }])
            mock.return_value = response
            person1, person2 = self.rsm.iterate(TestPerson)
            self.assertEqual(person1.uuid, 'person1')
            self.assertEqual(person1.age, 1)
            self.assertEqual(person1.name, 'person1')
            self.assertTrue(person1.is_read_only())

            self.assertEqual(person2.uuid, 'person2')
            self.assertEqual(person2.age, 2)
            self.assertEqual(person2.name, 'person2')
            self.assertTrue(person2.is_read_only())

            mock.assert_called_with(
                'GET', 'http://www.example.org/repos/foo/%s.json' % (
                    fqcn(TestPerson),))

    def test_get(self):
        with patch.object(self.rsm, 'mk_request') as mock:
            response = Response()
            response.encoding = 'utf-8'
            response._content = json.dumps({
                'uuid': 'person1',
                'age': 1,
                'name': 'person1'
            })
            mock.return_value = response
            person1 = self.rsm.get(TestPerson, 'person1')
            self.assertEqual(person1.uuid, 'person1')
            self.assertEqual(person1.age, 1)
            self.assertEqual(person1.name, 'person1')
            mock.assert_called_with(
                'GET', 'http://www.example.org/repos/foo/%s/person1.json' % (
                    fqcn(TestPerson),))
