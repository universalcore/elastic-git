def introspect_properties(model_class):
    """

    Introspect a :py:class:`elasticgit.models.Model` and
    retrieve a suitable mapping to use when indexing instances
    of the model in Elasticsearch.

    >>> from elasticgit.models import Model, TextField
    >>>
    >>> class TestModel(Model):
    ...     field = TextField('A text field')
    ...
    >>>
    >>> introspect_properties(TestModel) # doctest: +ELLIPSIS
    {'field': {'type': 'string'}, 'version': {'type': 'string'}, ...}
    >>>
    """
    return dict([
        (field_name, field_object.mapping)
        for field_name, field_object in model_class._fields.items()
    ])
