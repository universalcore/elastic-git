from zope.interface import implements
from elasticgit.istorage import IStorageManager


class RemoteStorageManager(object):
    implements(IStorageManager)

    def __init__(self, repo_url):
        self.repo_url = repo_url

    def write_config(self, section, data):
        pass

    def read_config(Self, section):
        pass

    def storage_exists(self):
        pass

    def destroy_storage(self):
        pass

    def iterate(self, model_class):
        pass

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
