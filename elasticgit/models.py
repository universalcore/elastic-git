import sys
import pkg_resources
from copy import deepcopy
from urllib2 import urlparse
import uuid

from confmodel.config import Config, ConfigField
from confmodel.errors import ConfigError
from confmodel.fallbacks import SingleFieldFallback


version_info = {
    'language': 'python',
    'language_version_string': sys.version,
    'language_version': '%d.%d.%d' % (
        sys.version_info.major,
        sys.version_info.minor,
        sys.version_info.micro,
    ),
    'package': 'elastic-git',
    'package_version': pkg_resources.require('elastic-git')[0].version
}


class ModelField(ConfigField):

    default_mapping = {
        'type': 'string',
    }

    def __init__(self, doc, required=False, default=None, static=False,
                 fallbacks=(), mapping={}, name=None):
        super(ModelField, self).__init__(
            doc, required=required, default=default, static=static,
            fallbacks=fallbacks)
        self.name = name
        self.mapping = self.__class__.default_mapping.copy()
        self.mapping.update(mapping)

    def __repr__(self):
        return '<%s.%s %r>' % (
            self.__class__.__module__, self.__class__.__name__, self.name)


class TextField(ModelField):
    """
    A text field
    """
    field_type = 'str'

    def clean(self, value):
        if not isinstance(value, str):
            self.raise_config_error("is not a string.")
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
        if isinstance(value, str):
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

    def __init__(self, doc, fields, default=[], static=False,
                 fallbacks=(), mapping={}):
        super(ListField, self).__init__(
            doc, default=default, static=static, fallbacks=fallbacks,
            mapping=mapping)
        self.fields = fields

    def clean(self, value):
        if isinstance(value, tuple):
            value = list(value)
        if not isinstance(value, list):
            self.raise_config_error("is not a list.")

        if len(value) > 0:
            for field in self.fields:
                if not any([field.clean(v) for v in value]):
                    self.raise_config_error(
                        'All field checks failed for some values.')
        return deepcopy(value)


class DictField(ModelField):
    """
    A dictionary field
    """
    field_type = 'dict'

    def __init__(self, doc, fields, default=None, static=False,
                 fallbacks=(), mapping=()):
        mapping = mapping or self.generate_default_mapping(fields)
        super(DictField, self).__init__(
            doc, default=default, static=static, fallbacks=fallbacks,
            mapping=mapping)
        self.fields = fields

    def generate_default_mapping(self, fields):
        field_names = [field.name for field in fields]
        return {
            'type': 'nested',
            'properties': dict(
                [(name, {'type': 'string'}) for name in field_names]),
        }

    def clean(self, value):
        if not isinstance(value, dict):
            self.raise_config_error('is not a dict.')
        return deepcopy(value)

    def validate(self, config):
        data = self.get_value(config)
        if data:
            for key, value in data.items():
                [field] = [field for field in self.fields if field.name == key]
                field.clean(value)


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
        if not isinstance(value, str):
            self.raise_config_error("is not a URL string.")
        # URLs must be bytes, not unicode.
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        return urlparse.urlparse(value)


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
    _version = DictField(
        'Model Version Identifier',
        default=version_info,
        fields=(
            TextField('language', name='language'),
            TextField('language_version_string',
                      name='language_version_string'),
            TextField('language_version', name='language_version'),
            TextField('package', name='package'),
            TextField('package_version', name='package_version'),
        ),
        mapping={
            'type': 'nested',
            'properties': {
                'language': {'type': 'string'},
                'language_version_string': {'type': 'string'},
                'language_version': {'type': 'string'},
                'package': {'type': 'string'},
                'package_version': {'type': 'string'}
            }
        })

    uuid = UUIDField('Unique Identifier')

    def __init__(self, config_data, static=False, es_meta=None):
        super(Model, self).__init__(config_data, static=static)
        self._read_only = False
        self.es_meta = es_meta

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
        """
        Mark this model instance as being read only.
        Returns self to allow it to be chainable.

        :returns: self
        """
        self._read_only = True
        return self

    def is_read_only(self):
        return self._read_only

    def __iter__(self):
        for field in self._get_fields():
            yield field.name, field.get_value(self)

    def compatible_version(self, own_version, check_version):
        own = map(int, own_version.split('.'))
        check = map(int, check_version.split('.'))
        return own >= check

    def post_validate(self):
        value = self._version
        current_version = version_info['package_version']
        package_version = value['package_version']
        if not self.compatible_version(current_version, package_version):
            raise ConfigError(
                'Got a version from the future, expecting: %r got %r' % (
                    current_version, package_version))
        super(Model, self).post_validate()


ConfigError
SingleFieldFallback
