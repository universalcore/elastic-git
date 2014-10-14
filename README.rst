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

We've followed the example of Apache Avro_ when it comes to schema evolution.
Avro compatible schema's can be generated from the command line.

Model definitions can be rebuilt from Avro_ JSON schema files.

A sample model file:

.. code-block:: python

    class TestPerson(Model):
        age = IntegerField('The Age')
        name = TextField('The name')

Generating the Avro_ spec file

.. code-block:: bash

    $ python -m elasticgit.tools dump-schema models.TestPerson > avro.json
    $ python -m elasticgit.tools load-schema avro.json > models.py

The generated model file:

.. code-block:: python

    # NOTE:
    #
    #   This is an automatically generated Elasticgit Model definition
    #   from an Avro schema. Do not manually edit this file unless you
    #   absolutely know what you are doing.
    #
    # timestamp: 2014-10-14T15:55:13.786029
    # namespace: elasticgit.tests.base
    # type: record
    # name: TestPerson
    #

    from elasticgit import models

    class TestPerson(models.Model):

        age = models.IntegerField(u"""The Age""")
        _version = models.ModelVersionField(u"""Model Version Identifier""", default={       u'language': u'python',
            u'language_version': u'2.7.6',
            u'language_version_string': u'2.7.6 (default, Dec 22 2013, 09:30:03) \n[GCC 4.2.1 Compatible Apple LLVM 5.0 (clang-500.2.79)]',
            u'package': u'elastic-git',
            u'package_version': u'0.1.3'})
        name = models.TextField(u"""The name""")
        uuid = models.TextField(u"""Unique Identifier""")

.. _Avro: avro.apache.org/docs/1.7.7/spec.html