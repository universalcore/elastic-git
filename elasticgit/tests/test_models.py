from elasticgit.tests.base import ModelBaseTest
from elasticgit.models import ConfigError, IntegerField, TextField


class TestModel(ModelBaseTest):

    def test_model(self):
        model_class = self.mk_model({
            'age': IntegerField('An age')
        })

        model = model_class({'age': 1})
        self.assertEqual(model._fields.keys(), ['age', 'uuid'])

    def test_validation(self):
        model_class = self.mk_model({
            'age': IntegerField('An age')
        })

        model = model_class({'age': 1})
        self.assertEqual(model.age, 1)
        self.assertRaises(ConfigError, model_class, {'age': 'foo'})

    def test_doc_generation(self):
        model_class = self.mk_model({
            'age': IntegerField('An age'),
            'name': TextField('A name'),
        })
        model = model_class({'age': 1, 'name': 'foo'})
        self.assertTrue(':param int age:' in model_class.__doc__)
        self.assertTrue(':param int age:' in model.__doc__)
        self.assertTrue(':param str name:' in model_class.__doc__)
        self.assertTrue(':param str name:' in model.__doc__)

    def test_to_dict(self):
        model_class = self.mk_model({
            'age': IntegerField('An age'),
            'name': TextField('A name'),
        })
        data = {'age': 1, 'name': 'foo'}
        model = model_class(data)
        self.assertEqual(dict(model), data)

    def test_uuids(self):
        model_class = self.mk_model({
            'age': IntegerField('An age'),
            'name': TextField('A name'),
        })
        data = {'age': 1, 'name': 'foo'}
        model = model_class(data)
        print model.uuid
