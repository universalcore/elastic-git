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
    ...     print person.name, person.age
    ...
    Bar 20
    Baz 30


Schema Management
-----------------

We've followed the example of Apache Avro when it comes to schema evolution.
Avro compatible schema's can be generated from the command line.

Model definitions can be rebuilt from Avro JSON schema files.

.. code-block:: bash

    $ python -m elasticgit.tools dump-schema \
        elasticgit.tests.base.TestPerson > avro.json
    $ python -m elasticgit.tools load-schema avro.json > models.py
