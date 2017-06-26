import os
import sys

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()

with open(os.path.join(here, 'VERSION')) as f:
    version = f.read().strip()

install_requires = [
    'confmodel==0.2.0',
    'elasticsearch==1.7.0',
    'elasticutils==0.10.1',
    'GitPython==1.0.2',
    'Jinja2',
    'requests',
    'six',
    'Unidecode==0.04.16',
    'zope.interface',
]
if sys.version_info[0] == 3:
    install_requires.append('avro-python3==1.7.7')
else:
    install_requires.append('avro==1.7.7')

setup(
    name='elastic-git',
    version=version,
    description='JSON Object storage backed by Git & Elastic Search',
    long_description=README,
    classifiers=[
        "Programming Language :: Python",
    ],
    author='Praekelt.org',
    author_email='dev@praekelt.org',
    url='http://github.com/universalcore/elastic-git',
    license='BSD',
    keywords='git elasticsearch json',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    entry_points={
      'console_scripts': ['eg-tools = elasticgit.tools:main'],
    }
)
