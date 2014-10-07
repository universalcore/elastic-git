import glob
import shutil
import os
import json
from git import Repo

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

    def load_all(self, model_class):
        """
        This should load all known instances of this model from disk
        because we need to know how to re-populate ES
        """
        return glob.iglob(self.file_path(model_class, '*.json'))

    def save(self, model, message):
        index = Repo(self.workdir).index

        # ensure the directory exists
        dirname = self.file_path(model.__class__)
        os.makedirs(dirname)

        # write the json
        with open(self.file_name(model), 'w') as fp:
            json.dump(dict(model), fp, indent=2)

        # add to the git index
        index.add([self.git_name(model)])
        return index.commit(message)

    def delete(self, model, message):
        index = Repo(self.workdir).index
        index.remove([self.git_name(model)])
        return index.commit(message)

    def storage_exists(self):
        return os.path.isdir(self.workdir)

    def create_storage(self, name, email, bare=False):
        if not os.path.isdir(self.workdir):
            os.makedirs(self.workdir)
        repo = Repo.init(self.workdir, bare)
        config = repo.config_writer()
        config.set_value("user", "name", name)
        config.set_value("user", "email", email)
        return repo.index.commit('Initialize repository.')

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
