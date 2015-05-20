Elastic Git
===========

Adventures in an declarative object-y thing backed by Git and using
Elasticsearch as a query backend.

.. note:: Here be massive dragons.

.. image:: https://travis-ci.org/universalcore/elastic-git.svg?branch=develop
    :target: https://travis-ci.org/universalcore/elastic-git
    :alt: Continuous Integration

.. image:: https://coveralls.io/repos/universalcore/elastic-git/badge.png?branch=develop
    :target: https://coveralls.io/r/universalcore/elastic-git?branch=develop
    :alt: Code Coverage

.. image:: https://readthedocs.org/projects/elastic-git/badge/?version=latest
    :target: https://elastic-git.readthedocs.org
    :alt: Elastic-Git Documentation

Usage
-----

.. code-block:: python

    from elasticgit import EG
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


Data is now persisted in a git repository and is queryable via elasticsearch:

.. code-block:: python

    >>> from elasticgit import EG
    >>> from elasticgit.tests.base import TestPerson as Person
    >>> workspace = EG.workspace('/Users/sdehaan/Desktop/test-repo/')
    >>> for person in workspace.S(Person).filter(age__gte=20):
    ...     print person.name, person.age
    ...
    Bar 20
    Baz 30

Check the ``examples/`` directory for some more code samples.

.. code-block:: bash

    $ python -m examples.basic_usage
    e6cb25f00870472fa5223d76dc361667 Baz 30
    2bd470372243411c9abd8fdcb969dcf5 Bar 20



Schema Management
-----------------

We've followed the example of Apache Avro_ when it comes to schema evolution.
Avro compatible schemas can be generated from the command line.

Model definitions can be rebuilt from Avro_ JSON schema files.

A sample model file:

.. code-block:: python

    class TestFallbackPerson(Model):
        age = IntegerField('The Age')
        name = TextField('The name', fallbacks=[
            SingleFieldFallback('nick'),
            SingleFieldFallback('obsolete'),
        ])
        nick = TextField('The nickname', required=False)
        obsolete = TextField('Some obsolete field', required=False)

Generating the Avro_ spec file

.. code-block:: bash

    $ python -m elasticgit.tools dump-schema \
    >   elasticgit.tests.base.TestFallbackPerson > avro.json
    $ python -m elasticgit.tools load-schema avro.json > models.py

The generated model file:

.. code-block:: python

    # NOTE:
    #
    #   This is an automatically generated Elasticgit Model definition
    #   from an Avro schema. Do not manually edit this file unless you
    #   absolutely know what you are doing.
    #
    # timestamp: 2014-10-14T18:51:23.916194
    # namespace: elasticgit.tests.base
    # type: record
    # name: TestFallbackPerson
    #

    from elasticgit import models

    class TestFallbackPerson(models.Model):

        name = models.TextField(u"""The name""", fallbacks=[models.SingleFieldFallback('nick'),models.SingleFieldFallback('obsolete'),])
        age = models.IntegerField(u"""The Age""")
        obsolete = models.TextField(u"""Some obsolete field""")
        _version = models.ModelVersionField(u"""Model Version Identifier""")
        nick = models.TextField(u"""The nickname""")
        uuid = models.TextField(u"""Unique Identifier""")

We're using ConfModel_'s fallbacks feature and encode this in Avro_'s
Schema as ``aliases``. This allows you to fall back to older names for
fields:

.. code-block:: python

    >>> TestFallbackPerson({'obsolete': 'oldest name', 'age': 10}).name
    'oldest name'
    >>> TestFallbackPerson({'nick': 'older name', 'age': 10}).name
    'older name'
    >>> TestFallbackPerson({'name': 'current name', 'age': 10}).name
    'current name'


.. _Avro: http://avro.apache.org/docs/1.7.7/spec.html
.. _ConfModel: http://confmodel.rtfd.org/
