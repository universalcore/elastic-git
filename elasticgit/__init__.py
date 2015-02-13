import pkg_resources

from elasticgit.workspace import EG, F, Q

__all__ = ['EG', 'F', 'Q']
__version__ = pkg_resources.require('elastic-git')[0].version
