.. Elastic Git documentation master file, created by
   sphinx-quickstart on Tue Oct  7 17:16:12 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


Welcome to Elastic Git's documentation!
=======================================

Elastic Git is a library for modelling data, storing it in git and querying
it via elastic search.

.. image:: https://travis-ci.org/universalcore/elastic-git.svg?branch=develop
    :target: https://travis-ci.org/universalcore/elastic-git
    :alt: Continuous Integration

.. image:: https://coveralls.io/repos/universalcore/elastic-git/badge.png?branch=develop
    :target: https://coveralls.io/r/universalcore/elastic-git?branch=develop
    :alt: Code Coverage

.. image:: https://readthedocs.org/projects/elastic-git/badge/?version=latest
    :target: https://elastic-git.readthedocs.org
    :alt: Elastic-Git Documentation


.. doctest::

   >>> from elasticgit import EG
   >>> from elasticgit.models import Model, IntegerField, TextField
   >>>
   >>> workspace = EG.workspace('.test_repo')
   >>> workspace.setup('Simon de Haan', 'simon@praekeltfoundation.org')
   >>>
   >>> # Models can be defined like
   >>> class Person(Model):
   ...     age = IntegerField('The Age')
   ...     name = TextField('The Name')
   ...
   >>> # But for doctests we're going to import an existing one
   >>> from elasticgit.tests.base import TestPerson as Person
   >>> person1 = Person({'age': 10, 'name': 'Foo'})
   >>> workspace.save(person1, 'Saving Person 1')
   >>>
   >>> person2 = Person({'age': 20, 'name': 'Bar'})
   >>> workspace.save(person2, 'Saving Person 2')
   >>>
   >>> person3 = Person({'age': 30, 'name': 'Baz'})
   >>> workspace.save(person3, 'Saving Person 3')
   >>>
   >>> # Elasticsearch does this automatically every few seconds
   >>> # but not fast enough for unit tests.
   >>> workspace.refresh_index()
   >>>
   >>> # Accessing the data ES knows about
   >>> es_person1, es_person2 = workspace.S(
   ...     Person).filter(age__gte=20).order_by('-name')
   >>> es_person1.name
   u'Baz'
   >>> es_person2.name
   u'Bar'
   >>>
   >>> # Accessing the actual Person object stored in Git
   >>> git_person1 = es_person1.get_object()
   >>> git_person1.name
   u'Baz'
   >>> git_person1.age
   30
   >>>
   >>> sorted(dict(git_person1).keys())
   ['_version', 'age', 'name', 'uuid']
   >>>

.. testcleanup::

   from elasticgit import EG

   workspace = EG.workspace('.test_repo')
   workspace.destroy()


.. toctree::
   :maxdepth: 2


   workspace
   models
   utils
   tools


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

