from elasticutils import get_es
from elasticgit.utils import introspect_properties

from elasticutils import MappingType, Indexable


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
        return cls.workspace.index.es

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
        return cls.workspace.storage.load_all(cls.model)


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


class GitManager(object):

    def __init__(self, workspace):
        self.workspace = workspace

    def load_all(self, model_class):
        """
        This should load all known instances of this model from disk
        because we need to know how to re-populate ES
        """
        return []


class Workspace(object):

    """
    I'm thinking this should have two different kinds of managers
    one a `.index` which provides an interface to all things ES
    and another `.storage` which provides an interface to all things Git
    """

    def __init__(self, workdir, es, index_name):
        self.index = ESManager(self, es)
        self.storage = GitManager(self)
        self.workdir = workdir
        self.index_name = index_name


class EG(object):

    @classmethod
    def workspace(self, workdir, es={}, index_name='elastic-git'):
        return Workspace(workdir, get_es(**es), index_name)
