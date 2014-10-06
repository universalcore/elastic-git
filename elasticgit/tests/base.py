from unittest import TestCase

from elasticgit.models import Model


class ModelBaseTest(TestCase):

    def mk_model(self, fields):
        return type('TempModel', (Model,), fields)
