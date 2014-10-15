import json


class Serializer(object):

    encoding = 'utf-8'

    def serialize(self, model):
        return self.dumps(dict(model))

    def deserialize(self, model_class, data):
        return model_class(self.loads(data))


class JSONSerializer(Serializer):

    suffix = 'json'

    def dumps(self, data):
        return json.dumps(data, indent=2, encoding=self.encoding)

    def loads(self, data):
        return json.loads(data, encoding=self.encoding)
