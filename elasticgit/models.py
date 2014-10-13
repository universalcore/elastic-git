import uuid

from confmodel.config import Config
from confmodel.errors import ConfigError
from confmodel.fields import (
    ConfigText, ConfigInt, ConfigFloat, ConfigBool, ConfigList,
    ConfigDict, ConfigUrl, ConfigRegex)

import elasticgit


class TextField(ConfigText):
    """
    A text field
    """

    #: Mapping for Elasticsearch
    mapping = {
        'type': 'string',
    }


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


class Model(Config):
    """
    Base model for all things stored in Git and Elasticsearch.
    A very thin wrapper around :py:class:`confmodel.Config`.

    Subclass this model and add more field as needed.

    :param dict config_data:
        A dictionary with keys & values to populate this Model
        instance with.
    """
    version = DictField(
        'Model Version Identifier', default=elasticgit.version_info)
    uuid = TextField('Unique Identifier')

    def post_validate(self):
        if not self.uuid:
            self._config_data['uuid'] = uuid.uuid4().hex
        self.validate()

    def validate(self):
        """
        Subclasses can subclass this to perform more validation checks.
        """

    def __eq__(self, other):
        return self._config_data == other._config_data

    def __iter__(self):
        for field in self._get_fields():
            yield field.name, field.get_value(self)

ConfigError
