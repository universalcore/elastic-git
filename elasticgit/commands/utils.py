from confmodel.config import ConfigMetaClass

from elasticgit.utils import load_class


def load_models(models):
    models_module = load_class(models)
    models = dict([
        (name, value)
        for name, value in models_module.__dict__.items()
        if isinstance(value, ConfigMetaClass)
    ])
    return models
