from copy import deepcopy
from urllib2 import urlparse
import uuid

from confmodel.config import Config, ConfigField
from confmodel.errors import ConfigError
from confmodel.fallbacks import SingleFieldFallback


import elasticgit


class ModelField(ConfigField):

    default_mapping = {
        'type': 'string',
    }

    def __init__(self, doc, required=False, default=None, static=False,
                 fallbacks=(), mapping={}):
        super(ModelField, self).__init__(
            doc, required=required, default=default, static=static,
            fallbacks=fallbacks)
        self.mapping = self.__class__.default_mapping.copy()
        self.mapping.update(mapping)


class TextField(ModelField):
    """
    A text field
    """
    field_type = 'str'

    def clean(self, value):
        if not isinstance(value, basestring):
            self.raise_config_error("is not a base string.")
        return value


class UnicodeTextField(ModelField):
    """
    A text field
    """
    field_type = 'unicode'

    def clean(self, value):
        if not isinstance(value, unicode):
            self.raise_config_error("is not unicode.")
        return value


class IntegerField(ModelField):
    """
    An integer field
    """
    field_type = 'int'

    #: Mapping for Elasticsearch
    default_mapping = {
        'type': 'integer',
    }

    def clean(self, value):
        try:
            # We go via "str" to avoid silently truncating floats.
            # XXX: Is there a better way to do this?
            return int(str(value))
        except (ValueError, TypeError):
            self.raise_config_error("could not be converted to int.")


class FloatField(ModelField):
    """
    A float field
    """
    field_type = 'float'

    #: Mapping for Elasticsearch
    default_mapping = {
        'type': 'float'
    }

    def clean(self, value):
        try:
            return float(value)
        except (ValueError, TypeError):
            self.raise_config_error("could not be converted to float.")


class BooleanField(ModelField):
    """
    A boolean field
    """
    field_type = 'bool'

    #: Mapping for Elasticsearch
    default_mapping = {
        'type': 'boolean'
    }

    def clean(self, value):
        if isinstance(value, basestring):
            return value.strip().lower() not in ('false', '0', '')
        return bool(value)


class ListField(ModelField):
    """
    A list field
    """
    field_type = 'list'

    #: Mapping for Elasticsearch
    default_mapping = {
        'type': 'string',
    }

    def clean(self, value):
        if isinstance(value, tuple):
            value = list(value)
        if not isinstance(value, list):
            self.raise_config_error("is not a list.")
        return deepcopy(value)


class DictField(ModelField):
    """
    A dictionary field
    """
    field_type = 'dict'

    #: Mapping for Elasticsearch
    default_mapping = {
        'type': 'string',
    }

    def clean(self, value):
        if not isinstance(value, dict):
            self.raise_config_error("is not a dict.")
        return deepcopy(value)


class URLField(ModelField):
    """
    A url field
    """
    field_type = 'URL'

    #: Mapping for Elasticsearch
    mapping = {
        'type': 'string',
    }

    def clean(self, value):
        if not isinstance(value, basestring):
            self.raise_config_error("is not a URL string.")
        # URLs must be bytes, not unicode.
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        return urlparse.urlparse(value)


class ModelVersionField(DictField):
    """
    A field holding the version information for a model
    """
    default_mapping = {
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
