import os
import urllib

from urlparse import urlparse

import requests

from zope.interface import implements

from elasticgit.istorage import IStorageManager
from elasticgit.utils import fqcn


class RemoteStorageException(Exception):
    pass


class RemoteStorageManager(object):
    implements(IStorageManager)

    def __init__(self, repo_url):
        self.repo_url = repo_url
        parse_result = urlparse(self.repo_url)
        self.scheme = parse_result.scheme
        self.host = parse_result.netloc
        self.port = parse_result.port
        self.dir_name = os.path.dirname(parse_result.path)
        basename = os.path.basename(parse_result.path)
        self.repo_name, _, self.suffix = basename.partition('.')

    def mk_request(self, *args, **kwargs):
        """
        Mocked out in tests
        """
        return requests.request(*args, **kwargs)

    def url(self, *parts):
        path = [self.repo_name]
        path.extend(parts)
        return '%s://%s%s%s/%s.%s' % (
            self.scheme,
            self.host,
            ':%s' % (self.port,) if self.port else '',
            self.dir_name,
            '/'.join(path),
            self.suffix
        )

    def write_config(self, section, data):
        raise RemoteStorageException(
            'Remote storage is read only.')

    def read_config(Self, section):
        raise RemoteStorageException(
            'Not implemented for remote storage.')

    def storage_exists(self):
        response = self.mk_request('GET', self.repo_url)
        return response.ok

    def destroy_storage(self):
        raise RemoteStorageException(
            'Remote storage is read only.')

    def iterate(self, model_class):
        response = self.mk_request('GET', self.url(fqcn(model_class)))
        response.raise_for_status()
        return [model_class(obj).set_read_only() for obj in response.json()]

    def get(self, model_class, uuid):
        response = self.mk_request('GET', self.url(fqcn(model_class), uuid))
        response.raise_for_status()
        return model_class(response.json()).set_read_only()

    def store(self, model, message, author=None, committer=None):
        raise RemoteStorageException(
            'Remote storage is read only.')

    def store_data(self, repo_path, data, message,
                   author=None, committer=None):
        raise RemoteStorageException(
            'Remote storage is read only.')

    def delete(self, model, message, author=None, committer=None):
        raise RemoteStorageException(
            'Remote storage is read only.')

    def delete_data(self, repo_path, message,
                    author=None, committer=None):
        raise RemoteStorageException(
            'Remote storage is read only.')

    def pull(self, branch_name='master', remote_name='origin'):
        response = self.mk_request('POST', '%s?%s' % (
            self.url(), urllib.urlencode({
                'branch': branch_name,
                'remote': remote_name,
            })))
        response.raise_for_status()
        return True
