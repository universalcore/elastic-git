import shutil
import os
from urllib import quote

from git import Repo

from elasticutils import MappingType, Indexable, get_es, S, Q, F

from elasticgit.serializers import JSONSerializer
from elasticgit.utils import introspect_properties, load_class


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

    def index_status(self, name):
        """
        Get an index status

        :param str name:
        """
        index_name = self.index_name(name)
        status = self.es.indices.status(index=index_name)
        index_status = status['indices'][index_name]
        return index_status

    def index_ready(self, name):
        """
        Check if an index is ready for use.

        :param str name:
        :returns: bool
        """
        status = self.index_status(name)
        # NOTE: ES returns a lot of nested info here, hence the complicated
        #       generator in generator
        return any([
            any([shard['state'] == 'STARTED' for shard in shard_slice])
            for shard_slice in status['shards'].values()
        ])

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

    def raw_unindex(self, model_class, uuid, refresh_index=False):
        """
        Remove an entry from the Elasticsearch index.
        This differs from :py:func:`.unindex` because it does not
        require an instance of :py:class:`elasticgit.models.Model`
        because you're likely in a position where you don't have it
        if you're trying to unindex it.

        :param elasticgit.models.Model model_class:
            The model class
        :param str uuid:
            The model's UUID
        :param bool refresh_index:
            Whether or not to manually refresh the Elasticsearch index.
            Useful in testing.
        """
        MappingType = self.get_mapping_type(model_class)
        MappingType.unindex(uuid)
        if refresh_index:
            MappingType.refresh_index()

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
        self.raw_unindex(model_class, model.uuid, refresh_index=refresh_index)
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

    def setup_mapping(self, name, model_class):
        """
        Specify a mapping for a model class in a specific index

        :param str name:
        :param elasticgit.models.Model model_class:
        :returns: dict
        """
        MappingType = self.get_mapping_type(model_class)
        return self.setup_custom_mapping(
            name, model_class, MappingType.get_mapping())

    def setup_custom_mapping(self, name, model_class, mapping):
        """
        Specify a mapping for a model class in a specific index

        :param str name:
        :param elasticgit.models.Model model_class:
        :param dict mapping: The Elasticsearch mapping definition
        :returns: dict
        """
        MappingType = self.get_mapping_type(model_class)
        return self.es.indices.put_mapping(
            index=self.index_name(name),
            doc_type=MappingType.get_mapping_type_name(),
            body=mapping)

    def get_mapping(self, name, model_class):
        """
        Retrieve a mapping for a model class in a specific index

        :param str name:
        :param elasticgit.models.Model model_class:
        :returns: dict
        """
        index_name = self.index_name(name)
        MappingType = self.get_mapping_type(model_class)
        data = self.es.indices.get_mapping(
            index=index_name,
            doc_type=MappingType.get_mapping_type_name())
        mappings = data[index_name]['mappings']
        return mappings[MappingType.get_mapping_type_name()]


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
        >>> from elasticgit.manager import StorageManager
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
        >>> from elasticgit.manager import StorageManager
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

    def load(self, file_path, model_class=None):
        """
        Load a file from the repository and return it as a Model instance.

        :param str file_path:
            The path of the object we want a model instance for.
        :returns:
            :py:class:`elasticgit.models.Model`
        """
        module_name, class_name, file_name = file_path.split('/', 3)
        uuid, suffix = file_name.split('.', 2)
        model_class = load_class('%s.%s' % (module_name, class_name))
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
        self.working_dir = self.repo.working_dir
        self.index_prefix = index_prefix

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
        Save a :py:class:`elasticgit.models.Model` instance in Git and add it
        to the Elasticsearch index.

        :param elasticgit.models.Model model:
            The model instance
        :param str message:
            The commit message to write the model to Git with.
        """
        self.sm.store(model, message)
        self.im.index(model)

    def delete(self, model, message):
        """
        Delete a :py:class`elasticgit.models.Model` instance from Git and
        the Elasticsearch index.

        :param elasticgit.models.Model model:
            The model instance
        :param str message:
            The commit message to remove the model from Git with.
        """
        self.sm.delete(model, message)
        self.im.unindex(model)

    def fast_forward(self, branch_name='master', remote_name='origin'):
        """
        Fetch & Merge in an upstream's commits.

        .. note::
            This should probably be renamed to `pull` instead as that
            is essentially what a ``fetch`` + ``merge`` is in Git.

        :param str branch_name:
            The name of the branch to fast forward & merge in
        :param str remote_name:
            The name of the remote to fetch from.
        """
        remote = self.repo.remote(name=remote_name)
        fetch_list = remote.fetch()
        fetch_info = fetch_list['%s/%s' % (remote_name, branch_name)]
        self.repo.git.merge(fetch_info.commit)

    def reindex_iter(self, model_class, refresh_index=True):
        """
        Reindex everything that Git knows about in an iterator

        :param elasticgit.models.Model model_class:
        :param bool refresh_index:
            Whether or not to refresh the index after everything has
            been indexed. Defaults to ``True``

        """
        branch = self.repo.active_branch
        if not self.im.index_exists(branch.name):
            self.im.create_index(branch.name)
        iterator = self.sm.iterate(model_class)
        for model in iterator:
            yield self.im.index(model)

        if refresh_index:
            self.refresh_index()

    def reindex(self, model_class, refresh_index=True):
        """
        Same as :py:func:`reindex_iter` but returns a list instead of
        a generator.
        """
        return list(
            self.reindex_iter(model_class, refresh_index=refresh_index))

    def refresh_index(self):
        """
        Manually refresh the Elasticsearch index. In production this is
        not necessary but it is useful when running tests.
        """
        self.im.refresh_indices(self.repo.active_branch.name)

    def index_ready(self):
        """
        Check if the index is ready

        :returns: bool
        """
        return self.im.index_ready(self.repo.active_branch.name)

    def sync(self, model_class, refresh_index=True):
        """
        Resync a workspace, it assumes the Git repository is the source
        of truth and Elasticsearch is made to match. This involves two
        passes, first to index everything that Git knows about and
        unindexing everything that's in Elastisearch that Git does not
        know about.

        :param elasticgit.models.Model model_class:
            The model to resync
        :param bool refresh_index:
            Whether or not to refresh the index after indexing
            everything from Git

        """
        reindexed_uuids = set([])
        removed_uuids = set([])

        for model_obj in self.reindex_iter(model_class,
                                           refresh_index=refresh_index):
            reindexed_uuids.add(model_obj.uuid)

        for result in self.S(model_class).everything():
            if result.uuid not in reindexed_uuids:
                self.im.raw_unindex(model_class, result.uuid)
                removed_uuids.add(result.uuid)

        return reindexed_uuids, removed_uuids

    def setup_mapping(self, model_class):
        """
        Add a custom mapping for a model_class

        :param elasticgit.models.Model model_class:
        :returns: dict, the decoded dictionary from Elasticsearch
        """
        return self.im.setup_mapping(self.repo.active_branch.name, model_class)

    def setup_custom_mapping(self, model_class, mapping):
        """
        Add a custom mapping for a model class instead of accepting
        what the model_class defines.

        :param elasticgit.models.Model model_class:
        :param dict: the Elastisearch mapping definition
        :returns: dict, the decoded dictionary from Elasticsearch
        """
        return self.im.setup_custom_mapping(
            self.repo.active_branch.name, model_class, mapping)

    def get_mapping(self, model_class):
        """
        Get a mapping from Elasticsearch for a model_class
        :param elasticgit.models.Model model_class:
        :returns: dict
        """
        return self.im.get_mapping(self.repo.active_branch.name, model_class)

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
    def workspace(cls, workdir, es={}, index_prefix=None):
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
        index_prefix = index_prefix or os.path.basename(workdir)
        repo = (cls.read_repo(workdir)
                if cls.is_repo(workdir)
                else cls.init_repo(workdir))
        return Workspace(repo, get_es(**es), index_prefix)

    @classmethod
    def dot_git_path(cls, workdir):
        return os.path.join(workdir, '.git')

    @classmethod
    def is_repo(cls, workdir):
        return cls.is_dir(cls.dot_git_path(workdir))

    @classmethod
    def is_dir(cls, workdir):
        return os.path.isdir(workdir)

    @classmethod
    def read_repo(cls, workdir):
        return Repo(workdir)

    @classmethod
    def init_repo(cls, workdir, bare=False):
        return Repo.init(workdir, bare=bare)

    @classmethod
    def clone_repo(cls, repo_url, workdir):
        return Repo.clone_from(repo_url, workdir)

Q
F
