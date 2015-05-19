import os
from datetime import datetime

from elasticutils import S as SBase

from elasticgit.tests.base import ModelBaseTest, TestPerson
from elasticgit.search import ReadOnlyModelMappingType, index_name, S, SM


class TestSearch(ModelBaseTest):

    def setUp(self):
        self.index_prefix1 = '%s-1' % self.mk_index_prefix()
        self.index_prefix2 = '%s-2' % self.mk_index_prefix()
        self.workspace1 = self.mk_workspace(
            index_prefix=self.index_prefix1,
            name=self.index_prefix1)
        self.workspace2 = self.mk_workspace(
            index_prefix=self.index_prefix2,
            name=self.index_prefix2)
        self.repo1 = self.workspace1.repo
        self.repo2 = self.workspace2.repo

    def test_init(self):
        repos = [self.repo1, self.repo2]
        repo_workdirs = map(lambda r: r.working_dir, repos)

        s_obj = SM(TestPerson, in_=repos)
        self.assertEqual(s_obj.repos, [self.repo1, self.repo2])
        self.assertEqual(s_obj.index_prefixes, [
            os.path.basename(self.repo1.working_dir),
            os.path.basename(self.repo2.working_dir)
        ])

        s_obj = SM(TestPerson, in_=repo_workdirs, index_prefixes=['i1', 'i2'])
        self.assertEqual(
            map(lambda r: r.working_dir, s_obj.repos),
            repo_workdirs)
        self.assertEqual(s_obj.index_prefixes, ['i1', 'i2'])

    def test_get_repo_indexes(self):
        index1 = index_name(self.index_prefix1, self.repo1.active_branch.name)
        index2 = index_name(self.index_prefix2, self.repo2.active_branch.name)
        default_index1 = index_name(
            os.path.basename(self.repo1.working_dir),
            self.repo1.active_branch.name)

        s_obj = SM(TestPerson, in_=[self.repo1])
        self.assertEqual(s_obj.get_repo_indexes(), [default_index1])

        s_obj = SM(
            TestPerson,
            in_=[self.repo1, self.repo2],
            index_prefixes=[self.index_prefix1, self.index_prefix2])
        self.assertEqual(
            s_obj.get_repo_indexes(),
            [index1, index2])
        self.assertEqual(
            index1,
            self.workspace1.im.index_name(self.repo1.active_branch.name))

    def test_get_indexes(self):
        s_obj = SM(TestPerson, in_=[self.repo1])
        self.assertEqual(
            s_obj.get_indexes(),
            [index_name(
                os.path.basename(self.repo1.working_dir),
                self.repo1.active_branch.name)])

    def test_mapping_type(self):
        s_obj = SM(TestPerson, in_=[self.repo1])
        self.assertTrue(issubclass(s_obj.type, ReadOnlyModelMappingType))

    def test_read_only(self):
        obj = ReadOnlyModelMappingType()
        self.assertRaises(NotImplementedError, obj.get_object)

    def test_to_python(self):
        person_es_data = {
            'age': 1,
            'name': u'2020-01-01T06:00:00',
            'uuid': u'foo',
        }
        person_es_data2 = person_es_data.copy()

        S_eg = S()
        S_original = SBase()
        eg_person = S_eg.to_python(person_es_data)
        original_person = S_original.to_python(person_es_data2)

        # check that both methods operate in place
        self.assertIs(person_es_data, eg_person)
        self.assertIs(original_person, person_es_data2)
        # check equality aside from datetime conversion
        self.assertIsInstance(eg_person.pop('name'), basestring)
        self.assertIsInstance(original_person.pop('name'), datetime)
        self.assertEqual(eg_person, original_person)

    def test_multi_index_query(self):
        excluded_workspace = self.mk_workspace()
        person1 = TestPerson({
            'age': 12,
            'name': 'Foo'
        })
        person2 = TestPerson({
            'age': 20,
            'name': 'Foo Foo'
        })
        person3 = TestPerson({
            'age': 25,
            'name': 'Foo Foo Foo'
            })
        self.workspace1.save(person1, 'Saving person 1')
        self.workspace2.save(person2, 'Saving person 2')
        excluded_workspace.save(person3, 'Saving person 3')
        # refreshes all indexes
        self.workspace1.im.es.indices.refresh()

        objects = SM(
            TestPerson,
            in_=[self.repo1, self.repo2],
            index_prefixes=[self.index_prefix1, self.index_prefix2]) \
            .everything()
        self.assertEqual(len(objects), 2)

        persons = [obj.to_object() for obj in objects]
        persons.sort(key=lambda p: p.age)
        self.assertEqual(
            persons,
            [person1, person2])
