from elasticgit.models import version_info
from elasticgit.tests.base import ModelBaseTest, TestPerson
from elasticgit.workspace import S


class TestIndex(ModelBaseTest):

    def setUp(self):
        self.workspace = self.mk_workspace()
        self.repo = self.workspace.repo
        self.branch = self.repo.active_branch
        self.im = self.workspace.im

    def test_exists(self):
        self.assertTrue(self.im.index_exists(self.branch.name))

    def test_create(self):
        self.im.destroy_index(self.branch.name)
        self.im.create_index(self.branch.name)
        self.assertTrue(self.im.index_exists(self.branch.name))

    def test_destroy(self):
        self.assertTrue(self.im.index_exists(self.branch.name))
        self.im.destroy_index(self.branch.name)
        self.assertFalse(self.im.index_exists(self.branch.name))

    def test_extract_document_with_object(self):
        person = TestPerson({
            'age': 1,
            'name': 'Kees',
        })
        self.workspace.save(person, 'Saving a person.')
        MappingType = self.im.get_mapping_type(TestPerson)
        data = MappingType.extract_document(person.uuid, person)
        self.assertEqual(data, {
            'age': 1,
            'name': 'Kees',
            'uuid': person.uuid,
            '_version': version_info,
        })

    def test_extract_document_with_object_id(self):
        person = TestPerson({
            'age': 1,
            'name': 'Kees',
        })
        self.workspace.save(person, 'Saving a person.')
        MappingType = self.im.get_mapping_type(TestPerson)
        data = MappingType.extract_document(person.uuid)
        self.assertEqual(data, {
            'age': 1,
            'name': 'Kees',
            'uuid': person.uuid,
            '_version': version_info,
        })

    def test_indexing(self):
        person = TestPerson({
            'age': 1,
            'name': 'Kees',
        })
        self.im.index(person, refresh_index=True)
        MappingType = self.im.get_mapping_type(TestPerson)
        self.assertEqual(
            S(MappingType).query(name__match='Kees').count(), 1)

    def test_unindexing(self):
        person1 = TestPerson({
            'age': 1,
            'name': 'Kees',
        })
        person2 = TestPerson({
            'age': 2,
            'name': 'Freek',
        })
        self.im.index(person1, refresh_index=True)
        self.im.index(person2, refresh_index=True)

        MappingType = self.im.get_mapping_type(TestPerson)
        self.assertEqual(
            S(MappingType).query(name__match='Kees').count(), 1)
        self.im.unindex(person1, refresh_index=True)
        self.assertEqual(
            S(MappingType).query(name__match='Kees').count(), 0)
        self.assertEqual(
            S(MappingType).count(), 1)
