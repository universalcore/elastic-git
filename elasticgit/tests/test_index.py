from elasticgit.tests.base import ModelBaseTest, TestPerson

from elasticutils import S

import elasticgit


class TestIndex(ModelBaseTest):

    def setUp(self):
        self.workspace = self.mk_workspace()
        self.repo = self.workspace.repo
        self.branch = self.repo.active_branch
        self.im = self.workspace.im

    def test_exists(self):
        self.assertFalse(self.im.index_exists(self.branch.name))

    def test_create(self):
        self.im.create_index(self.branch.name)
        self.assertTrue(self.im.index_exists(self.branch.name))

    def test_destroy(self):
        self.im.create_index(self.branch.name)
        self.assertTrue(self.im.index_exists(self.branch.name))
        self.im.destroy_index(self.branch.name)
        self.assertFalse(self.im.index_exists(self.branch.name))

    def test_extract_document_with_object(self):
        self.workspace.setup('Test Kees', 'kees@example.org')
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
            '_version': elasticgit.version_info,
        })

    def test_extract_document_with_object_id(self):
        self.workspace.setup('Test Kees', 'kees@example.org')
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
            '_version': elasticgit.version_info,
        })

    def test_indexing(self):
        self.workspace.setup('Test Kees', 'kees@example.org')
        person = TestPerson({
            'age': 1,
            'name': 'Kees',
        })
        self.im.index(person, refresh_index=True)
        MappingType = self.im.get_mapping_type(TestPerson)
        self.assertEqual(
            S(MappingType).query(name__match='Kees').count(), 1)

    def test_unindexing(self):
        self.workspace.setup('Test Kees', 'kees@example.org')
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
