"""
Welcome to Elastic Git's documentation!
=======================================

Elastic Git is a library for modelling data, storing it in git and querying
it via elastic search.

>>> from elasticgit import EG
>>> from elasticgit.models import Model, IntegerField, TextField
>>>
>>> workspace = EG.workspace('.test_repo')
>>> # putting this here because doctests don't have support for tearDown()
>>> workspace.destroy()
>>> workspace.setup('Simon de Haan', 'simon@praekeltfoundation.org')
>>>
>>> class Person(Model):
...     age = IntegerField('The Age')
...     name = TextField('The Name')
...
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
['age', 'name', 'uuid', 'version']
>>>
>>> workspace.destroy()
>>>

"""

import pkg_resources
import sys

from elasticgit.manager import EG

__all__ = ['EG']
__version__ = pkg_resources.require('elastic-git')[0].version

version_info = {
    'language': 'python',
    'language_version': '%d.%d.%d' % (
        sys.version_info.major,
        sys.version_info.minor,
        sys.version_info.micro,
    ),
    'package': 'elastic-git',
    'package_version': __version__
}
