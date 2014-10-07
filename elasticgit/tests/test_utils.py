from elasticgit.tests.base import ModelBaseTest
from elasticgit.models import IntegerField, TextField
from elasticgit.utils import introspect_properties


class TestUtils(ModelBaseTest):

    def assertMappingType(self, field_class, field_type):
        model_class = self.mk_model({
            'field_name': field_class('Foo'),
        })
        properties = introspect_properties(model_class)
        self.assertEqual(properties['field_name'], {
            'type': field_type
        })

    def test_introspect_integer(self):
        self.assertMappingType(IntegerField, 'integer')

    def test_introspect_string(self):
        self.assertMappingType(TextField, 'string')
