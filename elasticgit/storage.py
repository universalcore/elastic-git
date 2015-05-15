import os
import shutil
import logging

from git import Repo, Actor
from git.diff import DiffIndex

from elasticgit.models import Model
from elasticgit.serializers import JSONSerializer
from elasticgit.utils import load_class


log = logging.getLogger(__name__)


class StorageException(Exception):
    pass


class StorageRouter(object):

    def __init__(self, repos):
        self.repos = repos
        self.repo_by_name = dict(
            (os.path.basename(r.working_dir), r) for r in repos)

    def __call__(self, model=None, repo_name=None):
        if len(self.repos) == 1:
            return self.repos[0]

        repo_name = repo_name or os.path.basename(model._repo_path)
        repo = (None
                if not repo_name
                else self.repo_by_name.get(repo_name))
        if not repo:
            raise ValueError('Cannot route %r to a repo for storage' % model)
        return repo


class StorageManager(object):
    """
    An interface to :py:class:`elasticgit.models.Model` instances stored
    in Git.

    :param git.Repo repo:
        The repository to operate on.
    """

    serializer_class = JSONSerializer

    def __init__(self, repos):
        self.repos = repos
        self.repo = StorageRouter(repos)
        self.serializer = self.serializer_class()

    def git_path(self, model_class, *args):
        """
        Return the path of a model_class when layed out in the git
        repository.

        :param class model_class:
            The class to map to a path
        :param tuple args:
            Optional bits to join together after the path.
        :returns: str

        >>> from git import Repo
        >>> from elasticgit.tests.base import TestPerson
        >>> from elasticgit.storage import StorageManager
        >>> sm = StorageManager(Repo('.'))
        >>> sm.git_path(TestPerson)
        'elasticgit.tests.base/TestPerson'
        >>> sm.git_path(TestPerson, 'some-uuid.json')
        'elasticgit.tests.base/TestPerson/some-uuid.json'
        >>>

        """
        return os.path.join(
            model_class.__module__,
            model_class.__name__,
            *args)

    def git_name(self, model):
        """
        Return the file path to where the data for a
        :py:class:`elasticgit.models.Model` lives.

        :param elasticgit.models.Model model:
            The model instance
        :returns: str

        >>> from git import Repo
        >>> from elasticgit.tests.base import TestPerson
        >>> from elasticgit.storage import StorageManager
        >>> person = TestPerson({'age': 1, 'name': 'Foo', 'uuid': 'the-uuid'})
        >>> sm = StorageManager(Repo('.'))
        >>> sm.git_name(person)
        'elasticgit.tests.base/TestPerson/the-uuid.json'
        >>>

        """
        return self.git_path(
            model.__class__,
            '%s.%s' % (model.uuid, self.serializer.suffix))

    def iterate(self, model_class):
        """
        This loads all known instances of this model from Git
        because we need to know how to re-populate Elasticsearch.

        :param elasticgit.models.Model model_class:
            The class to look for instances of.

        :returns: generator
        """
        path = self.git_path(model_class, '*.%s' % (self.serializer.suffix,))
        for repo in self.repos:
            list_of_files = repo.git.ls_files(path)
            for file_path in filter(None, list_of_files.split('\n')):
                module_name, class_name, file_name = file_path.split('/', 3)
                uuid, suffix = file_name.split('.', 2)
                yield self.get(model_class, uuid)

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
                raise StorageException('%r does not subclass %r' % (
                    model_class, Model))
            return model_class, uuid
        except ValueError, e:
            log.warn('%s does not look like a model file path.' % (
                file_path,), exc_info=True)
        except ImportError, e:
            log.warn(e, exc_info=True)
        except StorageException, e:
            log.warn(e, exc_info=True)

    def load(self, file_path):
        """
        Load a file from the repository and return it as a Model instance.

        :param str file_path:
            The path of the object we want a model instance for.
        :returns:
            :py:class:`elasticgit.models.Model`
        """
        path_info = self.path_info(file_path)
        if path_info is None:
            raise StorageException(
                '%s does not look like a model file.' % (file_path,))

        return self.get(*path_info)

    def get_data(self, repo_path, repo=None):
        """
        Get the data for a file stored in git

        :param str repo_path:
            The path to the file in the Git repository
        :returns:
            str
        """
        repo = repo or self.repo()
        current_branch = repo.active_branch.name
        return repo.git.show('%s:%s' % (current_branch, repo_path))

    def get(self, model_class, uuid):
        """
        Get a model instance by loading the data from git and constructing
        the model_class

        :param elasticgit.models.Model model_class:
            The model class of which an instance to return
        :param str uuid:
            The uuid for the object to retrieve
        :returns:
            :py:class:elasticgit.models.Model
        """
        git_path = self.git_path(
            model_class, '%s.%s' % (uuid, self.serializer.suffix,))
        repo = filter(
            lambda r: os.path.exists(os.path.join(r.working_dir, git_path)),
            self.repos)
        if not repo:
            raise StorageException('%s object with uuid %s does not exist' % (
                model_class.__name__, uuid))
        if len(repo) > 1:
            raise StorageException(
                'Multiple repos contain %s object with uuid %s' % (
                    model_class.__name__, uuid))

        object_data = self.get_data(git_path, repo[0])
        model = self.serializer.deserialize(model_class, object_data)

        if model.uuid != uuid:
            raise StorageException(
                'Data uuid (%s) does not match requested uuid (%s).' % (
                    model.uuid, uuid))
        return model

    def store(self, model, message, author=None, committer=None,
              repo_name=None):
        """
        Store an instance's data in Git.

        :param elasticgit.models.Model model:
            The model instance
        :param str message:
            The commit message.
        :param tuple author:
            The author information (name, email address)
            Defaults repo default if unspecified.
        :param tuple committer:
            The committer information (name, email address).
            Defaults to the author if unspecified.
        :returns:
            The commit.
        """
        if not isinstance(message, str):
            raise StorageException('Messages need to be bytestrings.')

        if model.uuid is None:
            raise StorageException('Cannot save a model without a UUID set.')

        if model.is_read_only():
            raise StorageException('Trying to save a read only model.')

        if repo_name:
            repo = self.repo(repo_name=repo_name)
        else:
            repo = self.repo(model=model)
        model._repo_path = repo.working_dir

        return self.store_data(
            self.git_name(model),
            self.serializer.serialize(model),
            message,
            author=author, committer=committer, repo=repo)

    def store_data(self, repo_path, data, message,
                   author=None, committer=None, repo=None):
        """
        Store some data in a file

        :param str repo_path:
            Where to store the file.
        :param obj data:
            The data to write in the file.
        :param str message:
            The commit message.
        :param tuple author:
            The author information (name, email address)
            Defaults repo default if unspecified.
        :param tuple committer:
            The committer information (name, email address).
            Defaults to the author if unspecified.
        :returns:
            The commit
        """
        # ensure the directory exists
        repo = repo or self.repo()
        file_path = os.path.join(repo.working_dir, repo_path)
        dir_name = os.path.dirname(file_path)
        if not (os.path.isdir(dir_name)):
            os.makedirs(dir_name)

        with open(file_path, 'w') as fp:
            # write the object data
            fp.write(data)

        author_actor = Actor(*author) if author else None
        committer_actor = Actor(*committer) if committer else author_actor

        # add to the git index
        index = repo.index
        index.add([file_path])
        return index.commit(message,
                            author=author_actor,
                            committer=committer_actor)

    def delete(self, model, message, author=None, committer=None):
        """
        Delete a model instance from Git.

        :param elasticgit.models.Model model:
            The model instance
        :param str message:
            The commit message.
        :param tuple author:
            The author information (name, email address)
            Defaults repo default if unspecified.
        :param tuple committer:
            The committer information (name, email address).
            Defaults to the author if unspecified.
        :returns:
            The commit.
        """
        return self.delete_data(
            self.git_name(model), message, author=author, committer=committer,
            repo=self.repo(model=model))

    def delete_data(self, repo_path, message,
                    author=None, committer=None, repo=None):
        """
        Delete a file that's not necessarily a model file.

        :param str repo_path:
            Which file to delete.
        :param str message:
            The commit message.
        :param tuple author:
            The author information (name, email address)
            Defaults repo default if unspecified.
        :param tuple committer:
            The committer information (name, email address).
            Defaults to the author if unspecified.
        :returns:
            The commit
        """
        if not isinstance(message, str):
            raise StorageException('Messages need to be bytestrings.')

        repo = repo or self.repo()
        file_path = os.path.join(repo.working_dir, repo_path)
        if not os.path.isfile(file_path):
            raise StorageException('File does not exist.')

        author_actor = Actor(*author) if author else None
        committer_actor = Actor(*committer) if committer else author_actor

        # Remove from the index
        index = repo.index
        index.remove([file_path], working_tree=True)
        return index.commit(message,
                            author=author_actor,
                            committer=committer_actor)

    def storage_exists(self):
        """
        Check if the storage exists. Returns ``True`` if the directory
        exists, it does not check if it is an actual :py:class:`git.Repo`.

        :returns: bool
        """
        for repo in self.repos:
            if not os.path.isdir(repo.working_dir):
                return False
        return True

    def create_storage(self, bare=False):
        """
        Creates a new :py:class:`git.Repo`

        :param bool bare:
            Whether or not to create a bare repository. Defaults to ``False``.
        """
        init_commits = []
        for repo in self.repos:
            if not os.path.isdir(repo.working_dir):
                os.makedirs(repo.working_dir)
            repo = Repo.init(repo.working_dir, bare)
            init_commits.append(repo.index.commit('Initialize repository.'))
        return init_commits

    def write_config(self, section, data, repo_name=None):
        """
        Write a config block for a git repository.

        :param str section:
            The section to write the data for.
        :param dict data:
            The keys & values of data to write

        """
        repos = ([self.repo(repo_name=repo_name)]
                 if repo_name
                 else self.repos)
        for repo in repos:
            config_writer = repo.config_writer()
            for key, value in data.items():
                config_writer.set_value(section, key, value)
            config_writer.release()

    def read_config(self, section, repo_name=None):
        """
        Read a config block for a git repository.

        :param str section:
            The section to read.
        :returns: dict
        """
        repos = ([self.repo(repo_name=repo_name)]
                 if repo_name
                 else self.repos)
        data_all = []
        for repo in repos:
            config_reader = repo.config_reader()
            data = dict(config_reader.items(section))
            config_reader.release()
            data_all.append(data)
        return data_all

    def destroy_storage(self):
        """
        Destroy the repository's working dir.
        """
        for repo in self.repos:
            shutil.rmtree(repo.working_dir)

    def pull(self, branch_name='master', remote_name='origin'):
        """
        Fetch & Merge in an upstream's commits.

        :param str branch_name:
            The name of the branch to fast forward & merge in
        :param str remote_name:
            The name of the remote to fetch from.
        """
        # TODO - update for multiple repos
        remote = self.repo.remote(name=remote_name)
        fetch_list = remote.fetch()
        fetch_info = fetch_list['%s/%s' % (remote_name, branch_name)]

        # NOTE: This can happen when we've not done anything yet on a
        #       repository
        if self.repo.heads:
            hcommit = self.repo.head.commit
            diff = hcommit.diff(fetch_info.commit)
        else:
            diff = DiffIndex()

        self.repo.git.merge(fetch_info.commit)

        return diff
