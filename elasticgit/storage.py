import os
import shutil
import logging

from unidecode import unidecode

from git import Repo
from git.diff import DiffIndex

from elasticgit.models import Model
from elasticgit.serializers import JSONSerializer
from elasticgit.utils import load_class


log = logging.getLogger(__name__)


class StorageException(Exception):
    pass


class StorageManager(object):
    """
    An interface to :py:class:`elasticgit.models.Model` instances stored
    in Git.

    :param git.Repo repo:
        The repository to operate on.
    """

    serializer_class = JSONSerializer

    def __init__(self, repo):
        self.repo = repo
        self.workdir = self.repo.working_dir
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
        list_of_files = self.repo.git.ls_files(path)
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
                file_path,))
        except StorageException, e:
            log.warn(e)

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

    def get_data(self, repo_path):
        """
        Get the data for a file stored in git

        :param str repo_path:
            The path to the file in the Git repository
        :returns:
            str
        """
        current_branch = self.repo.active_branch.name
        return self.repo.git.show('%s:%s' % (current_branch, repo_path))

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

        object_data = self.get_data(
            self.git_path(
                model_class,
                '%s.%s' % (uuid, self.serializer.suffix,)))

        model = self.serializer.deserialize(model_class, object_data)

        if model.uuid != uuid:
            raise StorageException(
                'Data uuid (%s) does not match requested uuid (%s).' % (
                    model.uuid, uuid))
        return model

    def store(self, model, message):
        """
        Store an instance's data in Git.

        :param elasticgit.models.Model model:
            The model instance
        :param str message:
            The commit message.
        :returns:
            The commit.
        """
        if isinstance(message, unicode):
            message = unidecode(message)

        if model.uuid is None:
            raise StorageException('Cannot save a model without a UUID set.')

        if model.is_read_only():
            raise StorageException('Trying to save a read only model.')

        return self.store_data(
            self.git_name(model), self.serializer.serialize(model), message)

    def store_data(self, repo_path, data, message):
        """
        Store some data in a file

        :param str file_path:
            Where to store the file.
        :param obj data:
            The data to write in the file.
        :param str message:
            The commit message.
        :returns:
            The commit
        """

        # ensure the directory exists
        file_path = os.path.join(self.repo.working_dir, repo_path)
        dir_name = os.path.dirname(file_path)
        if not (os.path.isdir(dir_name)):
            os.makedirs(dir_name)

        with open(file_path, 'w') as fp:
            # write the object data
            fp.write(data)

        # add to the git index
        index = self.repo.index
        index.add([file_path])
        return index.commit(message)

    def delete(self, model, message):
        """
        Delete a model instance from Git.

        :param elasticgit.models.Model model:
            The model instance
        :param str message:
            The commit message.
        :returns:
            The commit.
        """
        if isinstance(message, unicode):
            message = unidecode(message)

        index = self.repo.index
        index.remove([self.git_name(model)])
        index.commit(message)
        return os.remove(
            os.path.join(self.workdir, self.git_name(model)))

    def storage_exists(self):
        """
        Check if the storage exists. Returns ``True`` if the directory
        exists, it does not check if it is an actual :py:class:`git.Repo`.

        :returns: bool
        """
        return os.path.isdir(self.workdir)

    def create_storage(self, bare=False):
        """
        Creates a new :py:class:`git.Repo` and sets the committers
        name & email.

        :param bool bare:
            Whether or not to create a bare repository. Defaults to ``False``.
        """
        if not os.path.isdir(self.workdir):
            os.makedirs(self.workdir)
        repo = Repo.init(self.workdir, bare)
        return repo.index.commit('Initialize repository.')

    def write_config(self, section, data):
        """
        Write a config block for a git repository.

        :param str section:
            The section to write the data for.
        :param dict data:
            The keys & values of data to write

        """
        config = self.repo.config_writer()
        for key, value in data.items():
            config.set_value(section, key, value)

    def read_config(self, section):
        """
        Read a config block for a git repository.

        :param str section:
            The section to read.
        :returns: dict
        """
        config = self.repo.config_reader()
        return dict(config.items(section))

    def destroy_storage(self):
        """
        Destroy the repository's working dir.
        """
        return shutil.rmtree(self.workdir)

    def pull(self, branch_name='master', remote_name='origin'):
        """
        Fetch & Merge in an upstream's commits.

        :param str branch_name:
            The name of the branch to fast forward & merge in
        :param str remote_name:
            The name of the remote to fetch from.
        """
        remote = self.repo.remote(name=remote_name)
        fetch_list = remote.fetch()
        if not fetch_list:
            return DiffIndex()

        # NOTE: This can happen when we've not done anything yet on a
        #       repository
        if not self.repo.heads:
            return DiffIndex()

        fetch_info = fetch_list['%s/%s' % (remote_name, branch_name)]
        hcommit = self.repo.head.commit
        diff = hcommit.diff(fetch_info.commit)
        self.repo.git.merge(fetch_info.commit)
        return diff
