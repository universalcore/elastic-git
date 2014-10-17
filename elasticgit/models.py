import uuid

from confmodel.config import Config
from confmodel.errors import ConfigError
from confmodel.fields import (
    ConfigText, ConfigInt, ConfigFloat, ConfigBool, ConfigList,
    ConfigDict, ConfigUrl, ConfigRegex)
from confmodel.fallbacks import SingleFieldFallback


import elasticgit


class TextField(ConfigText):
    """
    A text field
    """
    def __init__(self, doc, mapping={}, *args, **kwargs):
        super(TextField, self).__init__(doc, *args, **kwargs)

        #: Mapping for Elasticsearch
        self.mapping = {
            'type': 'string',
        }

        self.mapping.update(mapping)


class IntegerField(ConfigInt):
    """
    An integer field
    """

    #: Mapping for Elasticsearch
    mapping = {
        'type': 'integer',
    }


class FloatField(ConfigFloat):
    """
    A float field
    """

    #: Mapping for Elasticsearch
    mapping = {
        'type': 'float'
    }


class BooleanField(ConfigBool):
    """
    A boolean field
    """

    #: Mapping for Elasticsearch
    mapping = {
        'type': 'boolean'
    }


class ListField(ConfigList):
    """
    A list field
    """

    #: Mapping for Elasticsearch
    mapping = {
        'type': 'string',
    }


class DictField(ConfigDict):
    """
    A dictionary field
    """

    #: Mapping for Elasticsearch
    mapping = {
        'type': 'string',
    }


class URLField(ConfigUrl):
    """
    A url field
    """

    #: Mapping for Elasticsearch
    mapping = {
        'type': 'string',
    }


class RegexField(ConfigRegex):
    """
    A regex field
    """

    #: Mapping for Elasticsearch
    mapping = {
        'type': 'string',
    }


class ModelVersionField(DictField):
    """
    A field holding the version information for a model
    """
    mapping = {
        'type': 'nested',
        'properties': {
            'language': {'type': 'string'},
            'language_version_string': {'type': 'string'},
            'language_version': {'type': 'string'},
            'package': {'type': 'string'},
            'package_version': {'type': 'string'}
        }
    }

    def validate(self, config):
        config._config_data.setdefault(
            self.name, elasticgit.version_info.copy())
        value = self.get_value(config)
        current_version = elasticgit.version_info['package_version']
        package_version = value['package_version']
        if (current_version < package_version):
            raise ConfigError(
                'Got a version from the future, expecting: %r got %r' % (
                    current_version, package_version))
        return super(ModelVersionField, self).validate(config)


class UUIDField(TextField):

    def validate(self, config):
        config._config_data.setdefault(self.name, uuid.uuid4().hex)
        return super(UUIDField, self).validate(config)


class Model(Config):
    """
    Base model for all things stored in Git and Elasticsearch.
    A very thin wrapper around :py:class:`confmodel.Config`.

    Subclass this model and add more field as needed.

    :param dict config_data:
        A dictionary with keys & values to populate this Model
        instance with.
    """
    _version = ModelVersionField('Model Version Identifier')
    uuid = UUIDField('Unique Identifier')

    def __init__(self, config_data, static=False):
        super(Model, self).__init__(config_data, static=static)
        self._read_only = False

    def __eq__(self, other):
        own_data = dict(self)
        other_data = dict(other)
        own_version_info = own_data.pop('_version')
        other_version_info = other_data.pop('_version')
        return (own_data == other_data and
                own_version_info == other_version_info)

    def update(self, fields, mark_read_only=True):
        model_class = self.__class__
        data = dict(self)
        data.update(fields)
        new_instance = model_class(data)
        if mark_read_only:
            self.set_read_only()
        return new_instance

    def set_read_only(self):
        self._read_only = True

    def is_read_only(self):
        return self._read_only

    def __iter__(self):
        for field in self._get_fields():
            yield field.name, field.get_value(self)

ConfigError
SingleFieldFallback
