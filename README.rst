Elastic Git
===========

Adventures in an declarative object-y thing backed by Git and using Elastic
Search as a query backend.

.. note:: Here be massive dragons.

.. image:: https://travis-ci.org/smn/elastic-git.svg?branch=develop
    :target: https://travis-ci.org/smn/elastic-git

.. image:: https://coveralls.io/repos/smn/elastic-git/badge.png?branch=develop
  :target: https://coveralls.io/r/smn/elastic-git?branch=develop

.. image:: https://readthedocs.org/projects/elastic-git/badge/?version=latest
  :target: https://readthedocs.org/projects/elastic-git/?badge=latest
  :alt: Documentation Status

Usage
-----

.. code-block:: python

    from elasticgit.manager import EG
    from elasticgit.models import Model, IntegerField, TextField


    workspace = EG.workspace('/Users/sdehaan/Desktop/test-repo/')
    workspace.setup('Simon de Haan', 'simon@praekeltfoundation.org')


    """
    # The model looks like this

    class Person(Model):
        age = IntegerField('The Age')
        name = TextField('The Name')
    """
    from elasticgit.tests.base import TestPerson as Person

    person1 = Person({'age': 10, 'name': 'Foo'})
    workspace.save(person1, 'Saving Person 1')

    person2 = Person({'age': 20, 'name': 'Bar'})
    workspace.save(person2, 'Saving Person 2')

    person3 = Person({'age': 30, 'name': 'Baz'})
    workspace.save(person3, 'Saving Person 3')


Data is now persisted in a git repository and is queryable via elastic search:

.. code-block:: python

    >>> from elasticgit.manager import EG
    >>> from elasticgit.tests.base import TestPerson as Person
    >>> workspace = EG.workspace('/Users/sdehaan/Desktop/test-repo/')
    >>> for person in workspace.S(Person).filter(age__gte=20):
    ...     print person.get_object(), dict(person.get_object())
    ...
    <elasticgit.tests.base.TestPerson object at 0x10f906d90> {'age': 20, 'uuid': u'9890c5813fc14fcd82a3ec3751a1b1fe', 'name': u'Bar'}
    <elasticgit.tests.base.TestPerson object at 0x10f906d90> {'age': 30, 'uuid': u'4b5c33de63034205ac23b746ee93344b', 'name': u'Baz'}
    >>> for person in workspace.S(Person).query(name__match='Baz'):
    ...     print person.get_object(), dict(person.get_object())
    ...
    <elasticgit.tests.base.TestPerson object at 0x10f906d90> {'age': 30, 'uuid': u'4b5c33de63034205ac23b746ee93344b', 'name': u'Baz'}
    >>>

Git log output of the repository

.. code-block:: diff

    commit 89afa833e4c537293a5f21d4e867cd061ece82a9
    Author: Simon de Haan <simon@praekeltfoundation.org>
    Date:   Tue Oct 7 15:23:30 2014 +0200

        Saving Person 3

    diff --git a/elasticgit.tests.base/TestPerson/4b5c33de63034205ac23b746ee93344b.json b/elasticgit.tests.base/TestPerson/4b5c33de63034205ac23b746ee93344b.json
    new file mode 100644
    index 0000000..03d55b8
    --- /dev/null
    +++ b/elasticgit.tests.base/TestPerson/4b5c33de63034205ac23b746ee93344b.json
    @@ -0,0 +1,5 @@
    +{
    +  "age": 30,
    +  "uuid": "4b5c33de63034205ac23b746ee93344b",
    +  "name": "Baz"
    +}
    \ No newline at end of file

    commit bc3b779ade98dacfdcb181dd6a24bc4c9350bdd3
    Author: Simon de Haan <simon@praekeltfoundation.org>
    Date:   Tue Oct 7 15:23:28 2014 +0200

        Saving Person 2

    diff --git a/elasticgit.tests.base/TestPerson/9890c5813fc14fcd82a3ec3751a1b1fe.json b/elasticgit.tests.base/TestPerson/9890c5813fc14fcd82a3ec3751a1b1fe.json
    new file mode 100644
    index 0000000..3fb0070
    --- /dev/null
    +++ b/elasticgit.tests.base/TestPerson/9890c5813fc14fcd82a3ec3751a1b1fe.json
    @@ -0,0 +1,5 @@
    +{
    +  "age": 20,
    +  "uuid": "9890c5813fc14fcd82a3ec3751a1b1fe",
    +  "name": "Bar"
    +}
    \ No newline at end of file
