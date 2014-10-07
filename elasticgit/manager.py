import shutil
import os
import json
from git import Repo

from elasticutils import MappingType, Indexable, get_es, S, Q, F

from elasticgit.utils import introspect_properties


class ModelMappingType(MappingType, Indexable):

    @classmethod
    def get_index(cls):
        return cls.index_name

    @classmethod
    def get_mapping_type_name(cls):
        model = cls.model
        return '%s-%sType' % (
            model.__module__.replace(".", "-"),
            model.__name__)

    @classmethod
    def get_model(self):
        return self.model

    def get_object(self):
        return self.workspace.sm.get(self.model, self._id)

    @classmethod
    def get_es(cls):
        return cls.workspace.im.es

    @classmethod
    def get_mapping(cls):
        return {
            'properties': introspect_properties(cls.model)
        }

    @classmethod
    def extract_document(cls, obj_id, obj=None):
        if obj is None:
            obj = cls.workspace.sm.get(cls.model, obj_id)
        return dict(obj)

    @classmethod
    def get_indexable(cls):
        return cls.workspace.sm.iterate(cls.model)


class ESManager(object):
    """
    An interface to :py:class:`elasticgit.models.Model` instances stored
    in Git.

    :param elasticgit.manager.Workspace workspace:
        The workspace to operate on.
    :param elasticsearch.Elasticsearch es:
        An Elasticsearch client instance.
    """
    def __init__(self, workspace, es):
        self.workspace = workspace
        self.es = es

    def get_mapping_type(self, model_class):
        return type(
            '%sMappingType' % (model_class.__name__,),
            (ModelMappingType,), {
                'workspace': self.workspace,
                'index_name': self.workspace.index_name,
                'model': model_class,
            })

    def index_exists(self):
        """
        Check if the index already exists in Elasticsearch
        :returns: bool
        """
        return self.es.indices.exists(index=self.workspace.index_name)

    def create_index(self):
        """
        Creates the index in Elasticsearch
        """
        return self.es.indices.create(index=self.workspace.index_name)

    def destroy_index(self):
        """
        Destroys the index in Elasticsearch
        """
        return self.es.indices.delete(index=self.workspace.index_name)

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


class StorageException(Exception):
    pass


class StorageManager(object):
    """
    An interface to :py:class:`elasticgit.models.Model` instances stored
    in Git.

    :param elasticgit.manager.Workspace workspace:
        The workspace to operate on.
    """

    def __init__(self, workspace):
        self.workspace = workspace
        self.workdir = self.workspace.workdir
        self.gitdir = os.path.join(self.workdir, '.git')

    def git_path(self, model_class, *args):
        return os.path.join(
            model_class.__module__,
            model_class.__name__,
            *args)

    def file_path(self, model_class, *args):
        return os.path.join(
            self.workdir,
            self.git_path(model_class, *args))

    def git_name(self, model):
        return self.git_path(model.__class__, '%s.json' % (model.uuid,))

    def file_name(self, model):
        return self.file_path(model.__class__, '%s.json' % (model.uuid,))

    def iterate(self, model_class):
        """
        This loads all known instances of this model from Git
        because we need to know how to re-populate Elasticsearch.

        :param elasticgit.models.Model model_class:
            The class to look for instances of.

        :returns: generator
        """
        repo = Repo(self.workdir)
        list_of_files = repo.git.ls_files(self.git_path(model_class, '*.json'))
        for file_path in filter(None, list_of_files.split('\n')):
            yield self.load(repo, file_path)

    def load(self, repo, file_path):
        """
        Load a file from the repository and return it as a Model instance.

        :param git.Repo repo:
            The repository to load models from.
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
        repo = Repo(self.workdir)
        current_branch = repo.head.reference

        json_data = repo.git.show(
            '%s:%s' % (
                current_branch,
                self.git_path(model_class, '%s.json' % (uuid,))))

        data = json.loads(json_data)

        if data['uuid'] != uuid:
            raise StorageException(
                'Data uuid (%s) does not match requested uuid (%s).' % (
                    data['uuid'], uuid))
        return model_class(data)

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

        index = Repo(self.workdir).index

        # ensure the directory exists
        dirname = self.file_path(model.__class__)
        try:
            os.makedirs(dirname)
        except OSError:
            pass

        # write the json
        with open(self.file_name(model), 'w') as fp:
            json.dump(dict(model), fp, indent=2)

        # add to the git index
        index.add([self.git_name(model)])
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
        index = Repo(self.workdir).index
        index.remove([self.git_name(model)])
        return index.commit(message)

    def storage_exists(self):
        """
        Check if the storage exists. Returns ``True`` if the directory
        exists, it does not check if it is an actual :py:class:`git.Repo`.
        """
        return os.path.isdir(self.workdir)

    def create_storage(self, name, email, bare=False):
        """
        Creates a new :py:class:`git.Repo` and sets the committers
        name & email.

        :param str name:
        :param str email:
        :param bool bare:
            Whether or not to create a bare repository. Defaults to ``False``.
        """
        if not os.path.isdir(self.workdir):
            os.makedirs(self.workdir)
        repo = Repo.init(self.workdir, bare)
        config = repo.config_writer()
        config.set_value("user", "name", name)
        config.set_value("user", "email", email)
        return repo.index.commit('Initialize repository.')

    def destroy_storage(self):
        """
        Destroy the repository's working dir.
        """
        return shutil.rmtree(self.workdir)


class Workspace(object):
    """
    The main API exposing a model interface to both a Git repository
    and an Elasticsearch index.

    :param str workdir:
        The path to the directory where a git repository can
        be found or needs to be created when
        :py:meth:`.Workspace.setup` is called.
    :param elasticsearch.Elasticsearch es:
        An Elasticsearch object.
    :param str index_name:
        The index to store documents under in Elasticsearch
    """

    def __init__(self, workdir, es, index_name):
        self.workdir = workdir
        self.index_name = index_name

        self.im = ESManager(self, es)
        self.sm = StorageManager(self)

    def setup(self, name, email):
        """
        Setup a Git repository & ES index if they do not yet exist.
        This is safe to run if already existing.

        :param str name:
            The name of the committer in this repository.
        :param str email:
            The email address of the committer in this repository.
        """
        if not self.im.index_exists():
            self.im.create_index()

        if not self.sm.storage_exists():
            self.sm.create_storage(name, email)

    def exists(self):
        """
        Check if the Git repository or the ES index exists.
        Returns ``True`` if either of them exist.

        :returns: bool
        """
        return any([self.im.index_exists(), self.sm.storage_exists()])

    def destroy(self):
        """
        Removes an ES index and a Git repository completely.
        Guaranteed to remove things completely, use with caution.
        """
        if self.im.index_exists():
            self.im.destroy_index()

        if self.sm.storage_exists():
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
        self.im.es.indices.refresh(index=self.index_name)

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
        return S(self.im.get_mapping_type(model_class))


class EG(object):

    """
    A helper function for things in ElasticGit.

    .. note::
        Very likely to get deprecated as it's not adding all
        that much value at the moment.

    """
    @classmethod
    def workspace(self, workdir, es={}, index_name='elastic-git'):
        """
        Create a workspace

        :param str workdir:
            The path to the directory where a git repository can
            be found or needs to be created when
            :py:meth:`.Workspace.setup` is called.
        :param dict es:
            The parameters to pass along to :func:`elasticutils.get_es`
        :param str index_name:
            The index to store things under in Elasticsearch.
        :returns:
            :py:class:`.Workspace`
        """
        return Workspace(workdir, get_es(**es), index_name)

Q
F
