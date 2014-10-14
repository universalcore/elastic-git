import shutil
import os
from urllib import quote

from git import Repo

from elasticutils import MappingType, Indexable, get_es, S, Q, F

from elasticgit.serializers import JSONSerializer
from elasticgit.utils import introspect_properties


class ModelMappingType(MappingType, Indexable):

    @classmethod
    def get_index(cls):
        im = cls.im
        repo = cls.sm.repo
        return im.index_name(repo.active_branch.name)

    @classmethod
    def get_mapping_type_name(cls):
        model_class = cls.model_class
        return '%s-%sType' % (
            model_class.__module__.replace(".", "-"),
            model_class.__name__)

    @classmethod
    def get_model(self):
        return self.model_class

    def get_object(self):
        return self.sm.get(self.model_class, self._id)

    @classmethod
    def get_es(cls):
        return cls.im.es

    @classmethod
    def get_mapping(cls):
        return {
            'properties': introspect_properties(cls.model_class)
        }

    @classmethod
    def extract_document(cls, obj_id, obj=None):
        if obj is None:
            obj = cls.sm.get(cls.model_class, obj_id)
        return dict(obj)

    @classmethod
    def get_indexable(cls):
        return cls.sm.iterate(cls.model_class)


class ESManager(object):
    """
    An interface to :py:class:`elasticgit.models.Model` instances stored
    in Git.

    :param elasticgit.manager.Workspace workspace:
        The workspace to operate on.
    :param elasticsearch.Elasticsearch es:
        An Elasticsearch client instance.
    """
    def __init__(self, storage_manager, es, index_prefix):
        self.sm = storage_manager
        self.es = es
        self.index_prefix = index_prefix

    def get_mapping_type(self, model_class):
        return type(
            '%sMappingType' % (model_class.__name__,),
            (ModelMappingType,), {
                'im': self,
                'sm': self.sm,
                'model_class': model_class,
            })

    def index_exists(self, name):
        """
        Check if the index already exists in Elasticsearch

        :param str name:
        :returns: bool
        """
        return self.es.indices.exists(index=self.index_name(name))

    def create_index(self, name):
        """
        Creates the index in Elasticsearch

        :param str name:
        """
        return self.es.indices.create(index=self.index_name(name))

    def destroy_index(self, name):
        """
        Destroys the index in Elasticsearch

        :param str name:
        """
        return self.es.indices.delete(index=self.index_name(name))

    def index(self, model, refresh_index=False):
        """
        Index a :py:class:`elasticgit.models.Model` instance in Elasticsearch

        :param elasticgit.models.Model model:
            The model instance
        :param bool refresh_index:
            Whether or not to manually refresh the Elasticsearch index.
            Useful in testing.
        :returns:
            :py:class:`elasticgit.models.Model`
        """
        model_class = model.__class__
        MappingType = self.get_mapping_type(model_class)
        MappingType.index(
            MappingType.extract_document(model.uuid, model), id_=model.uuid)
        if refresh_index:
            MappingType.refresh_index()
        return model

    def unindex(self, model, refresh_index=False):
        """
        Remove a :py:class:`elasticgit.models.Model` instance from the
        Elasticsearch index.

        :param elasticgit.models.Model model:
            The model instance
        :param bool refresh_index:
            Whether or not to manually refresh the Elasticsearch index.
            Useful in testing.
        :returns:
            :py:class:`elasticgit.models.Model`
        """
        model_class = model.__class__
        MappingType = self.get_mapping_type(model_class)
        MappingType.unindex(model.uuid)
        if refresh_index:
            MappingType.refresh_index()
        return model

    def index_name(self, name):
        """
        Generate an Elasticsearch index name using given name and prefixing
        it with the ``index_prefix``. The resulting generated index name
        is URL quoted.

        :param str name:
            The name to use for the index.
        """
        return '-'.join(map(quote, [self.index_prefix, name]))

    def refresh_indices(self, name):
        """
        Manually refresh the Elasticsearch index. In production this is
        not necessary but it is useful when running tests.

        :param str name:
        """
        return self.es.indices.refresh(index=self.index_name(name))


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
            yield self.load(file_path)

    def load(self, file_path):
        """
        Load a file from the repository and return it as a Model instance.

        :param str file_path:
            The path of the object we want a model instance for.
        :returns:
            :py:class:`elasticgit.models.Model`
        """
        module_name, class_name, file_name = file_path.split('/', 3)
        uuid, suffix = file_name.split('.', 2)
        mod = __import__(module_name, fromlist=[class_name])
        model_class = getattr(mod, class_name)
        return self.get(model_class, uuid)

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
        current_branch = self.repo.active_branch.name

        object_data = self.repo.git.show(
            '%s:%s' % (
                current_branch,
                self.git_path(
                    model_class,
                    '%s.%s' % (uuid, self.serializer.suffix,))))

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
        if model.uuid is None:
            raise StorageException('Cannot save a model without a UUID set.')

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
        index = self.repo.index
        index.remove([self.git_name(model)])
        return index.commit(message)

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


class Workspace(object):
    """
    The main API exposing a model interface to both a Git repository
    and an Elasticsearch index.

    :param git.Repo repo:
        A :py:class:`git.Repo` instance.
    :param elasticsearch.Elasticsearch es:
        An Elasticsearch object.
    :param str index_prefix:
        The prefix to use when generating index names for Elasticsearch
    """

    def __init__(self, repo, es, index_prefix):
        self.repo = repo
        self.sm = StorageManager(repo)
        self.im = ESManager(self.sm, es, index_prefix)

    def setup(self, name, email):
        """
        Setup a Git repository & ES index if they do not yet exist.
        This is safe to run if already existing.

        :param str name:
            The name of the committer in this repository.
        :param str email:
            The email address of the committer in this repository.
        """
        if not self.sm.storage_exists():
            self.sm.create_storage()

        self.sm.write_config('user', {
            'name': name,
            'email': email,
        })

        if not self.im.index_exists(self.repo.active_branch.name):
            self.im.create_index(self.repo.active_branch.name)

    def exists(self):
        """
        Check if the Git repository or the ES index exists.
        Returns ``True`` if either of them exist.

        :returns: bool
        """
        if self.sm.storage_exists():
            branch = self.sm.repo.active_branch
            return self.im.index_exists(branch.name)

        return False

    def destroy(self):
        """
        Removes an ES index and a Git repository completely.
        Guaranteed to remove things completely, use with caution.
        """
        if self.sm.storage_exists():
            branch = self.sm.repo.active_branch
            if self.im.index_exists(branch.name):
                self.im.destroy_index(branch.name)
            self.sm.destroy_storage()

    def save(self, model, message):
        """
        Save a :py:class:`elasticgit.Model` instance in Git and add it
        to the Elasticsearch index.

        :param str message:
            The commit message to write the model to Git with.
        """
        self.sm.store(model, message)
        self.im.index(model)

    def refresh_index(self):
        """
        Manually refresh the Elasticsearch index. In production this is
        not necessary but it is useful when running tests.
        """
        self.im.refresh_indices(self.repo.active_branch.name)

    def S(self, model_class):
        """
        Get a :py:class:`elasticutils.S` object for the given
        model class. Under the hood this dynamically generates a
        :py:class:`elasticutils.MappingType` and
        :py:class:`elasticutils.Indexable` subclass which maps the
        Elasticsearch results to :py:class:`elasticgit.models.Model`
        instances on the UUIDs.

        :param elasticgit.models.Model model_class:
            The class to provide a search interface for.
        """
        return S(
            self.im.get_mapping_type(model_class))


class EG(object):

    """
    A helper function for things in ElasticGit.

    """
    @classmethod
    def workspace(cls, workdir, es={}, index_prefix='elastic-git'):
        """
        Create a workspace

        :param str workdir:
            The path to the directory where a git repository can
            be found or needs to be created when
            :py:meth:`.Workspace.setup` is called.
        :param dict es:
            The parameters to pass along to :func:`elasticutils.get_es`
        :param str index_prefix:
            The index_prefix use when generating index names for
            Elasticsearch
        :returns:
            :py:class:`.Workspace`
        """
        repo = (cls.read_repo(workdir)
                if cls.is_repo(workdir)
                else cls.init_repo(workdir))
        return Workspace(repo, get_es(**es), index_prefix)

    @classmethod
    def is_repo(cls, workdir):
        return os.path.isdir(os.path.join(workdir, '.git'))

    @classmethod
    def read_repo(cls, workdir):
        return Repo(workdir)

    @classmethod
    def init_repo(cls, workdir, bare=False):
        if not cls.is_repo(workdir):
            os.makedirs(workdir)
        return Repo.init(workdir, bare)

Q
F
