import json


class Serializer(object):

    encoding = 'utf-8'

    def serialize(self, model, fp):
        return self.dump(dict(model), fp)

    def deserialize(self, model_class, data):
        return model_class(self.loads(data))


class JSONSerializer(Serializer):

    suffix = 'json'

    def dump(self, data, fp):
        return json.dump(data, fp=fp, indent=2, encoding=self.encoding)

    def loads(self, data):
        return json.loads(data, encoding=self.encoding)
