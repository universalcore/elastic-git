import os
from urlparse import urlparse

import requests

from zope.interface import implements

from elasticgit.istorage import IStorageManager
from elasticgit.utils import fqcn


class RemoteStorageManagerException(Exception):
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
        raise RemoteStorageManagerException(
            'Remote storage is read only.')

    def read_config(Self, section):
        raise RemoteStorageManagerException(
            'Not implemented for remote storage.')

    def storage_exists(self):
        response = self.mk_request('GET', self.repo_url)
        return response.status_code == requests.codes.ok

    def destroy_storage(self):
        raise RemoteStorageManagerException(
            'Remote storage is read only.')

    def iterate(self, model_class):
        return self.url(fqcn(model_class))

    def get(self, model_class, uuid):
        pass

    def store(self, model, message, author=None, committer=None):
        pass

    def store_data(self, repo_path, data, message,
                   author=None, committer=None):
        pass

    def delete(self, model, message, author=None, committer=None):
        pass

    def delete_data(self, repo_path, message,
                    author=None, committer=None):
        pass

    def pull(self, branch_name='master', remote_name='origin'):
        pass

    def path_info(self, path):
        pass
