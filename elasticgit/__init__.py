import pkg_resources
import sys

from elasticgit.manager import EG

__all__ = ['EG']
__version__ = pkg_resources.require('elastic-git')[0].version

version_info = {
    'language': 'python',
    'language_version_string': sys.version,
    'language_version': '%d.%d.%d' % (
        sys.version_info.major,
        sys.version_info.minor,
        sys.version_info.micro,
    ),
    'package': 'elastic-git',
    'package_version': __version__
}
