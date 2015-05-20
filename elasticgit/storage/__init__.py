from elasticgit.storage.local import (
    StorageManager, StorageException)
from elasticgit.storage.remote import (
    RemoteStorageManager, RemoteStorageException)

__all__ = ['StorageManager', 'RemoteStorageManager',
           'StorageException', 'RemoteStorageException']
