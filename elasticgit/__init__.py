"""
Welcome to Elastic Git's documentation!
=======================================

Elastic Git is a library for modelling data, storing it in git and querying
it via elastic search.

>>> from elasticgit.manager import EG
>>> from elasticgit.models import Model, IntegerField, TextField
>>>
>>> workspace = EG.workspace('/Users/sdehaan/Desktop/test-repo/')
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
>>> person1, person2 = workspace.S(
...     Person).filter(age__gte=20).order_by('-name')
>>> person1.name
u'Baz'
>>> person2.name
u'Bar'
>>> workspace.destroy()

"""
