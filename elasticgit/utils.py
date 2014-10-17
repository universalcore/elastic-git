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
    >>> from elasticgit.utils import introspect_properties
    >>>
    >>> introspect_properties(TestModel) # doctest: +ELLIPSIS
    {'field': {'type': 'string'}, '_version': {'type': 'nested', ...}
    >>>
    """
    return dict([
        (field_name, field_object.mapping)
        for field_name, field_object in model_class._fields.items()
    ])


def load_class(class_path):
    """
    Load a class by it's class path

    :param str class_path:
        The dotted.path.to.TheClass

    >>> from elasticgit.utils import load_class
    >>> load_class('elasticgit.tests.base.TestPerson')
    <class 'elasticgit.tests.base.TestPerson'>
    >>>

    """
    module_name, class_name = class_path.rsplit('.', 1)
    mod = __import__(module_name, fromlist=[class_name])
    return getattr(mod, class_name)


def fqcn(klass):
    """
    Given a class give it's fully qualified class name in dotted notation.
    The inverse of `load_class`

    :param class klass:

    >>> from elasticgit.utils import fqcn
    >>> from elasticgit.tests.base import TestPerson
    >>> fqcn(TestPerson)
    'elasticgit.tests.base.TestPerson'
    >>>

    """
    return '%s.%s' % (klass.__module__, klass.__name__)