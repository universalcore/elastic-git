import shutil
import os
import json
from git import Repo

from elasticutils import MappingType, Indexable, get_es, S

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
            obj = cls.workspace.using(cls.model).get(obj_id)
        return dict(obj)

    @classmethod
    def get_indexable(cls):
        return cls.workspace.sm.iterate(cls.model)


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

    def index(self, model, refresh_index=False):
        model_class = model.__class__
        MappingType = self.get_mapping_type(model_class)
        MappingType.index(dict(model), id_=model.uuid)
        if refresh_index:
            MappingType.refresh_index()
        return model

    def unindex(self, model, refresh_index=False):
        model_class = model.__class__
        MappingType = self.get_mapping_type(model_class)
        MappingType.unindex(model.uuid)
        if refresh_index:
            MappingType.refresh_index()
        return model


class StorageException(Exception):
    pass


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

    def iterate(self, model_class):
        """
        This should load all known instances of this model from disk
        because we need to know how to re-populate ES
        """
        repo = Repo(self.workdir)
        list_of_files = repo.git.ls_files(self.git_path(model_class, '*.json'))
        for file_path in filter(None, list_of_files.split('\n')):
            yield self.load(repo, file_path)

    def load(self, repo, file_path):
        module_name, class_name, file_name = file_path.split('/', 3)
        uuid, suffix = file_name.split('.', 2)
        mod = __import__(module_name, fromlist=[class_name])
        model_class = getattr(mod, class_name)
        return self.get(model_class, uuid)

    def get(self, model_class, uuid):
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

    def save(self, model, message):
        self.sm.store(model, message)
        self.im.index(model)

    def refresh_index(self):
        return self.im.es.indices.refresh(index=self.index_name)

    def S(self, model_class):
        return S(self.im.get_mapping_type(model_class))


class EG(object):

    @classmethod
    def workspace(self, workdir, es={}, index_name='elastic-git'):
        return Workspace(workdir, get_es(**es), index_name)
