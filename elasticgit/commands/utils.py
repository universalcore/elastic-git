import inspect

from elasticgit.commands.base import ToolCommandError
from elasticgit.models import Model
from elasticgit.utils import load_class


def load_models(models):
    models_module = load_class(models)
    models = dict([
        (name, value)
        for name, value in models_module.__dict__.items()
        if inspect.isclass(value) and issubclass(value, Model)
    ])
    return models


class ClassType(object):
    """
    Helper class for loading python classes in argparse command line
    arguments

    >>> from elasticgit.commands.utils import ClassType
    >>> from unittest import TestCase
    >>> loader = ClassType(TestCase)
    >>> loader('elasticgit.tests.base.ModelBaseTest')
    <class 'elasticgit.tests.base.ModelBaseTest'>
    >>>

    """

    def __init__(self, class_type):
        self.class_type = class_type

    def __call__(self, fqcn):
        model_class = load_class(fqcn)
        if not issubclass(model_class, self.class_type):
            raise ToolCommandError('%s does not subclass %s' % (
                model_class, self.class_type))
        return model_class


class ModelClassType(ClassType):
    """
    Helper class for loading model classes in argparse command line
    arguments

    >>> from elasticgit.commands.utils import ModelClassType
    >>> loader = ModelClassType()
    >>> loader('elasticgit.tests.base.TestPerson')
    <class 'elasticgit.tests.base.TestPerson'>
    >>>
    """

    def __init__(self):
        super(ModelClassType, self).__init__(Model)


class BooleanType(object):
    """
    Helper class for specify booleans on the command line.

    >>> from elasticgit.commands.utils import BooleanType
    >>> checker = BooleanType()
    >>> checker('yes')
    True
    >>> checker('no')
    False
    >>> checker('true')
    True
    >>> checker('false')
    False
    >>> checker('t')
    True
    >>> checker('f')
    False
    >>> checker('1')
    True
    >>> checker('0')
    False
    >>>

    """


    def __call__(self, value):
        return value.lower() in ("yes", "true", "t", "1")
