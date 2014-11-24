import pkg_resources
import sys

from elasticgit.workspace import EG, F, Q

__all__ = ['EG', 'F', 'Q']
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
