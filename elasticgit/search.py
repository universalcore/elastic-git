from urllib import quote

from elasticutils import MappingType, Indexable

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
