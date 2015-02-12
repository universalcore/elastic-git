from elasticgit.tests.base import ModelBaseTest
from elasticgit.models import (
    ConfigError, IntegerField, TextField, ListField, version_info)


class TestModel(ModelBaseTest):

    def test_model(self):
        model_class = self.mk_model({
            'age': IntegerField('An age')
        })

        model = model_class({'age': 1})
        self.assertEqual(
            set(model._fields.keys()),
            set(['_version', 'age', 'uuid']))

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
        data = {'age': 1, 'name': 'foo', '_version': version_info}
        model = model_class(data)
        self.assertEqual(dict(model), data)

    def test_creating_uuids(self):
        model_class = self.mk_model({
            'age': IntegerField('An age'),
            'name': TextField('A name'),
        })
        data = {'age': 1, 'name': 'foo'}
        model = model_class(data)
        self.assertTrue(model.uuid)

    def test_respecting_uuids(self):
        model_class = self.mk_model({
            'uuid': 'foo',
            'age': IntegerField('An age'),
            'name': TextField('A name'),
        })
        data = {'age': 1, 'name': 'foo'}
        model = model_class(data)
        self.assertEqual(model.uuid, 'foo')

    def test_update(self):
        model_class = self.mk_model({
            'uuid': 'foo',
            'age': IntegerField('An age'),
            'name': TextField('A name'),
        })
        data = {'age': 1, 'name': 'foo'}
        model = model_class(data)
        self.assertFalse(model.is_read_only())
        new_model = model.update({'age': 20})
        self.assertEqual(new_model.age, 20)
        self.assertEqual(new_model.uuid, model.uuid)
        self.assertEqual(new_model.name, model.name)
        self.assertTrue(model.is_read_only())
        self.assertFalse(new_model.is_read_only())

    def test_version_check(self):
        model_class = self.mk_model({})
        model = model_class({})
        self.assertTrue(model.compatible_version('0.2.10', '0.2.9'))
        self.assertTrue(model.compatible_version('0.2.10', '0.2.10'))
        self.assertFalse(model.compatible_version('0.2.9', '0.2.10'))

    def test_list_field(self):
        model_class = self.mk_model({
            'tags': ListField('list field', fields=(
                IntegerField('int'),
            ))
        })
        self.assertRaises(ConfigError, model_class, {'tags': ['a']})
        self.assertRaises(ConfigError, model_class, {'tags': [2.0]})
        self.assertRaises(ConfigError, model_class, {'tags': [None]})
        self.assertTrue(model_class({'tags': []}))
        self.assertTrue(model_class({'tags': [1, 2, 3]}))
        self.assertTrue(model_class({'tags': ['1']}))
