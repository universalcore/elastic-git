import os
import logging

import requests

from zope.interface import implements

from elasticgit.models import Model
from elasticgit.istorage import IStorageManager
from elasticgit.utils import fqcn, load_class

from six.moves import urllib


log = logging.getLogger(__name__)


class RemoteStorageException(Exception):
    pass


class RemoteStorageManager(object):
    implements(IStorageManager)

    def __init__(self, repo_url):
        self.repo_url = repo_url
        parse_result = urllib.parse.urlparse(self.repo_url)
        self.scheme = parse_result.scheme
        self.netloc = parse_result.netloc
        self.port = parse_result.port
        self.dir_name = os.path.dirname(parse_result.path)
        basename = os.path.basename(parse_result.path)
        self.repo_name, _, self.suffix = basename.partition('.')

    def mk_request(self, *args, **kwargs):
        """
        Mocked out in tests
        """
        return requests.request(*args, **kwargs)

    def active_branch(self):
        response = self.mk_request('GET', self.url())
        response.raise_for_status()
        return response.json()['branch']

    def url(self, *parts):
        path = [self.repo_name]
        path.extend(parts)
        return '%s://%s%s/%s.%s' % (
            self.scheme,
            self.netloc,
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

    def path_info(self, file_path):
        """
        Analyze a file path and return the object's class and the uuid.

        :param str file_path:
            The path of the object we want a model instance for.
        :returns:
            (model_class, uuid) tuple or ``None`` if not a model file path.
        """
        try:
            module_name, class_name, file_name = file_path.split('/', 3)
            uuid, suffix = file_name.split('.', 2)
            model_class = load_class('%s.%s' % (module_name, class_name))
            if not issubclass(model_class, Model):
                raise RemoteStorageException('%r does not subclass %r' % (
                    model_class, Model))
            return model_class, uuid
        except ValueError as e:
            log.warn('%s does not look like a model file path.' % (
                file_path,), exc_info=True)
        except ImportError as e:
            log.warn(e, exc_info=True)
        except RemoteStorageException as e:
            log.warn(e, exc_info=True)

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
        return response.json()
