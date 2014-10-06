import uuid
from confmodel.config import Config
from confmodel.errors import ConfigError
from confmodel.fields import (
    ConfigText, ConfigInt, ConfigFloat, ConfigBool, ConfigList,
    ConfigDict, ConfigUrl, ConfigRegex)


class TextField(ConfigText):
    pass


class IntegerField(ConfigInt):
    pass


class FloatField(ConfigFloat):
    pass


class BooleanField(ConfigBool):
    pass


class ListField(ConfigList):
    pass


class DictField(ConfigDict):
    pass


class URLField(ConfigUrl):
    pass


class RegexField(ConfigRegex):
    pass


class Model(Config):

    uuid = TextField('Unique Identifier')

    def post_validate(self):
        if not self.uuid:
            self._config_data['uuid'] = uuid.uuid4().hex

    def __iter__(self):
        for field in self._get_fields():
            yield field.name, field.get_value(self)

ConfigError
