from elasticgit import EG
from elasticgit.tests.base import TestPerson


if __name__ == '__main__':

    workspace = EG.workspace('.test_repo')
    workspace.destroy()
    # putting this here because doctests don't have support for tearDown()
    workspace.setup('Simon de Haan', 'simon@praekeltfoundation.org')

    person1 = TestPerson({'age': 10, 'name': 'Foo'})
    workspace.save(person1, 'Saving Person 1')

    person2 = TestPerson({'age': 20, 'name': 'Bar'})
    workspace.save(person2, 'Saving Person 2')

    person3 = TestPerson({'age': 30, 'name': 'Baz'})
    workspace.save(person3, 'Saving Person 3')

    # Elasticsearch does this automatically every few seconds
    # but not fast enough for unit tests.
    workspace.refresh_index()

    for person in workspace.S(TestPerson).filter(age__gte=20):
        print person.uuid, person.name, person.age

    workspace.destroy()
