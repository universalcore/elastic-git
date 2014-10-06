import glob
import shutil
import os.path
import json
import pygit2

from elasticutils import get_es
from elasticutils import MappingType, Indexable

from elasticgit.utils import introspect_properties


class ModelMappingType(MappingType, Indexable):

    @classmethod
    def get_index(cls):
        return cls.index_name

    @classmethod
    def get_mapping_type_name(cls):
        model = cls.model
        return '%s.%s-type' % (
            model.__module__,
            model.__name__)

    @classmethod
    def get_model(self):
        return self.model

    def get_object(self):
        return self.workspace.using(self.model).get(self._id)

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
            obj = cls.workspace.using(cls.model).get(obj_id)
        return dict(obj)

    @classmethod
    def get_indexable(cls):
        return cls.workspace.sm.load_all(cls.model)


class ESManager(object):

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
        return self.es.indices.exists(index=self.workspace.index_name)

    def create_index(self):
        return self.es.indices.create(index=self.workspace.index_name)

    def destroy_index(self):
        return self.es.indices.delete(index=self.workspace.index_name)


class StorageManager(object):

    def __init__(self, workspace):
        self.workspace = workspace
        self.workdir = self.workspace.workdir
        self.gitdir = os.path.join(self.workdir, '.git')
        self._repo = None

    @property
    def repo(self):
        if self._repo is not None:
            return self._repo
        self._repo = pygit2.Repository(self.gitdir)
        return self._repo

    def file_path(self, model_class, *args):
        return os.path.join(
            self.workdir,
            model_class.__module__,
            model_class.__class__.__name__,
            *args)

    def file_name(self, model):
        return self.file_path(model.__class__, '%s.json' % (model.uuid,))

    def load_all(self, model_class):
        """
        This should load all known instances of this model from disk
        because we need to know how to re-populate ES
        """
        return glob.iglob(self.file_path(model_class, '*.json'))

    def save(self, model, name, email, message):
        oid = self.repo.write(
            pygit2.GIT_OBJ_BLOB, json.dumps(dict(model), indent=2))
        tree = pygit2.TreeBuilder()
        tree.insert(self.file_name(model), oid, 100644)
        signature = pygit2.Signature(name, email)
        reference = 'refs/heads/master'
        parent_ref = self.repo.lookup_reference(reference)
        self.repo.create_commit(
            reference, signature, signature, message, tree.write(),
            [parent_ref.oid])

    def storage_exists(self):
        return os.path.isdir(self.workdir)

    def create_storage(self, name, email, bare=False,
                       commit_message='Initialize repository.'):
        repo = pygit2.init_repository(self.gitdir, bare)
        author = pygit2.Signature(name, email)
        tree = repo.TreeBuilder().write()
        repo.create_commit(
            'refs/heads/master',
            author, author, commit_message, tree, [])
        return repo

    def destroy_storage(self):
        return shutil.rmtree(self.workdir)


class Workspace(object):

    """
    I'm thinking this should have two different kinds of managers
    one a `.im` which provides an interface to all things ES
    and another `.sm` which provides an interface to all things Git
    """

    def __init__(self, workdir, es, index_name):
        self.workdir = workdir
        self.index_name = index_name

        self.im = ESManager(self, es)
        self.sm = StorageManager(self)

    def setup(self, name, email):
        if not self.im.index_exists():
            self.im.create_index()

        if not self.sm.storage_exists():
            self.sm.create_storage(name, email)
        return (self.im, self.sm)

    def exists(self):
        return any([self.im.index_exists(), self.sm.storage_exists()])

    def destroy(self):
        if self.im.index_exists():
            self.im.destroy_index()

        if self.sm.storage_exists():
            self.sm.destroy_storage()


class EG(object):

    @classmethod
    def workspace(self, workdir, es={}, index_name='elastic-git'):
        return Workspace(workdir, get_es(**es), index_name)
