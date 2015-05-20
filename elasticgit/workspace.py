import os
import warnings
from urlparse import urljoin

from unidecode import unidecode

from git import Repo

from elasticutils import get_es, Q, F

from elasticgit.storage import StorageManager, RemoteStorageManager
from elasticgit.search import ESManager, S

import logging

log = logging.getLogger(__name__)


class Workspace(object):
    """
    The main API exposing a model interface to both a Git repository
    and an Elasticsearch index.

    :param git.Repo repo:
        A :py:class:`git.Repo` instance.
    :param dit es:
        A dictionary of values one would pass to elasticutils.get_es
        to get an Elasticsearch connection
    :param str index_prefix:
        The prefix to use when generating index names for Elasticsearch
    """

    def __init__(self, repo, es, index_prefix):
        self.repo = repo
        self.sm = StorageManager(repo)
        self.es_settings = es
        self.im = ESManager(
            self.sm, get_es(**self.es_settings), index_prefix)
        self.working_dir = self.repo.working_dir
        self.index_prefix = index_prefix

    def setup(self, name, email):
        """
        Setup a Git repository & ES index if they do not yet exist.
        This is safe to run if already existing.

        :param str name:
            The name of the committer in this repository.
        :param str email:
            The email address of the committer in this repository.
        """
        if not self.sm.storage_exists():
            self.sm.create_storage()

        self.sm.write_config('user', {
            'name': name,
            'email': email,
        })

        if not self.im.index_exists(self.sm.active_branch()):
            self.im.create_index(self.sm.active_branch())

    def exists(self):
        """
        Check if the Git repository or the ES index exists.
        Returns ``True`` if either of them exist.

        :returns: bool
        """
        if self.sm.storage_exists():
            return self.im.index_exists(self.sm.active_branch())

        return False

    def destroy(self):
        """
        Removes an ES index and a Git repository completely.
        Guaranteed to remove things completely, use with caution.
        """
        if self.sm.storage_exists():
            if self.im.index_exists(self.sm.active_branch()):
                self.im.destroy_index(self.sm.active_branch())
            self.sm.destroy_storage()

    def save(self, model, message, author=None, committer=None):
        """
        Save a :py:class:`elasticgit.models.Model` instance in Git and add it
        to the Elasticsearch index.

        :param elasticgit.models.Model model:
            The model instance
        :param str message:
            The commit message to write the model to Git with.
        :param tuple author:
            The author information (name, email address)
            Defaults repo default if unspecified.
        :param tuple committer:
            The committer information (name, email address).
            Defaults to the author if unspecified.
        """
        if isinstance(message, unicode):
            message = unidecode(message)
        self.sm.store(model, message, author=author, committer=committer)
        self.im.index(model)

    def delete(self, model, message, author=None, committer=None):
        """
        Delete a :py:class`elasticgit.models.Model` instance from Git and
        the Elasticsearch index.

        :param elasticgit.models.Model model:
            The model instance
        :param str message:
            The commit message to remove the model from Git with.
        :param tuple author:
            The author information (name, email address)
            Defaults repo default if unspecified.
        :param tuple committer:
            The committer information (name, email address).
            Defaults to the author if unspecified.
        """
        if isinstance(message, unicode):
            message = unidecode(message)
        self.sm.delete(model, message, author=author, committer=committer)
        self.im.unindex(model)

    def fast_forward(self, branch_name='master', remote_name='origin'):
        warnings.warn('This method is deprecated, use pull() instead',
                      DeprecationWarning)
        return self.pull(branch_name=branch_name, remote_name=remote_name)

    def reindex_diff(self, diff_index):
        changed_model_set = set([])
        for diff in diff_index:
            if diff.new_file:
                path_info = self.sm.path_info(diff.b_blob.path)
                if path_info is not None:
                    changed_model_set.add(path_info[0])
            elif diff.renamed:
                path_info = self.sm.path_info(diff.a_blob.path)
                if path_info is not None:
                    changed_model_set.add(path_info[0])
            else:
                path_info = self.sm.path_info(diff.a_blob.path)
                if path_info is not None:
                    changed_model_set.add(path_info[0])

        for model_class in changed_model_set:
            self.reindex(model_class)

    def pull(self, branch_name='master', remote_name='origin'):
        """
        Fetch & Merge in an upstream's commits.

        :param str branch_name:
            The name of the branch to fast forward & merge in
        :param str remote_name:
            The name of the remote to fetch from.
        """
        changes = self.sm.pull(branch_name=branch_name,
                               remote_name=remote_name)

        # NOTE: This is probably more complicated than it needs to be
        #       If we have multiple remotes GitPython gets confused about
        #       deletes. It marks things as deletes because it may not
        #       exist on another remote.
        #
        #       Here we loop over all changes, track the models that've
        #       changed and then reindex fully to make sure we're in sync.
        if len(self.repo.remotes) > 1 and any(changes):
            return self.reindex_diff(changes)

        # NOTE: There's a very unlikely scenario where we're dealing with
        #       renames. This generally can only happen when a repository
        #       has been manually modififed. If that's the case then
        #       reindex everything as well
        if any(changes.iter_change_type('R')):
            return self.reindex_diff(changes)

        # unindex deleted blobs
        for diff in changes.iter_change_type('D'):
            path_info = self.sm.path_info(diff.a_blob.path)
            if path_info is None:
                continue
            self.im.raw_unindex(*path_info)

        # reindex added blobs
        for diff in changes.iter_change_type('A'):
            path_info = self.sm.path_info(diff.b_blob.path)
            if path_info is None:
                continue
            obj = self.sm.get(*path_info)
            self.im.index(obj)

        # reindex modified blobs
        for diff in changes.iter_change_type('M'):
            path_info = self.sm.path_info(diff.a_blob.path)
            if path_info is None:
                continue
            obj = self.sm.get(*path_info)
            self.im.index(obj)

    def reindex_iter(self, model_class, refresh_index=True):
        """
        Reindex everything that Git knows about in an iterator

        :param elasticgit.models.Model model_class:
        :param bool refresh_index:
            Whether or not to refresh the index after everything has
            been indexed. Defaults to ``True``

        """
        if not self.im.index_exists(self.sm.active_branch()):
            self.im.create_index(self.sm.active_branch())
        iterator = self.sm.iterate(model_class)
        for model in iterator:
            yield self.im.index(model)

        if refresh_index:
            self.refresh_index()

    def reindex(self, model_class, refresh_index=True):
        """
        Same as :py:func:`reindex_iter` but returns a list instead of
        a generator.
        """
        return list(
            self.reindex_iter(model_class, refresh_index=refresh_index))

    def refresh_index(self):
        """
        Manually refresh the Elasticsearch index. In production this is
        not necessary but it is useful when running tests.
        """
        self.im.refresh_indices(self.sm.active_branch())

    def index_ready(self):
        """
        Check if the index is ready

        :returns: bool
        """
        return self.im.index_ready(self.sm.active_branch())

    def sync(self, model_class, refresh_index=True):
        """
        Resync a workspace, it assumes the Git repository is the source
        of truth and Elasticsearch is made to match. This involves two
        passes, first to index everything that Git knows about and
        unindexing everything that's in Elastisearch that Git does not
        know about.

        :param elasticgit.models.Model model_class:
            The model to resync
        :param bool refresh_index:
            Whether or not to refresh the index after indexing
            everything from Git

        """
        reindexed_uuids = set([])
        removed_uuids = set([])

        for model_obj in self.reindex_iter(model_class,
                                           refresh_index=refresh_index):
            reindexed_uuids.add(model_obj.uuid)

        for result in self.S(model_class).everything():
            if result.uuid not in reindexed_uuids:
                self.im.raw_unindex(model_class, result.uuid)
                removed_uuids.add(result.uuid)

        return reindexed_uuids, removed_uuids

    def setup_mapping(self, model_class):
        """
        Add a custom mapping for a model_class

        :param elasticgit.models.Model model_class:
        :returns: dict, the decoded dictionary from Elasticsearch
        """
        return self.im.setup_mapping(self.sm.active_branch(), model_class)

    def setup_custom_mapping(self, model_class, mapping):
        """
        Add a custom mapping for a model class instead of accepting
        what the model_class defines.

        :param elasticgit.models.Model model_class:
        :param dict: the Elastisearch mapping definition
        :returns: dict, the decoded dictionary from Elasticsearch
        """

        return self.im.setup_custom_mapping(
            self.sm.active_branch(), model_class, mapping)

    def get_mapping(self, model_class):
        """
        Get a mapping from Elasticsearch for a model_class
        :param elasticgit.models.Model model_class:
        :returns: dict
        """
        return self.im.get_mapping(self.sm.active_branch(), model_class)

    def S(self, model_class):
        """
        Get a :py:class:`elasticutils.S` object for the given
        model class. Under the hood this dynamically generates a
        :py:class:`elasticutils.MappingType` and
        :py:class:`elasticutils.Indexable` subclass which maps the
        Elasticsearch results to :py:class:`elasticgit.models.Model`
        instances on the UUIDs.

        :param elasticgit.models.Model model_class:
            The class to provide a search interface for.
        """
        return S(
            self.im.get_mapping_type(model_class)).es(**self.es_settings)


class RemoteWorkspace(Workspace):
    """
    A workspace that connects to a unicore.distribute server hosted
    somewhere on the network.

    This is a read only version of the :py:class:`Workspace`
    """
    def __init__(self, url, es=None, index_prefix=None):
        """
        :param str url:
            The URL of the unicore.distribute server.
        :param dict es:
            The parameters for connecting to Elasticsearch to. If not specified
            then the default unicore.distribute ES proxy would be used.
            This defaults to ``/esapi`` on the host of the ``url`` parameter
            provided.
        :param str index_prefix:
            The prefix to use when generating index names for Elasticsearch
        """
        self.sm = RemoteStorageManager(url)
        self.index_prefix = index_prefix or self.sm.repo_name
        self.es_settings = es or {'urls': urljoin(url, '/esapi')}
        self.im = ESManager(
            self.sm,
            es=get_es(**self.es_settings),
            index_prefix=self.index_prefix)

    def pull(self, branch_name='master', remote_name='origin'):
        # TOOD: In the local storage we're diffing the changes pulled in
        #       So that we can re-index those, unicore.distribute doesn't
        #       expose that diff yet and so we cannot yet reindex.
        import warnings
        warnings.warn('Pulling without updating the index!')
        self.sm.pull(branch_name=branch_name,
                     remote_name=remote_name)


class EG(object):

    """
    A helper function for things in ElasticGit.

    """
    @classmethod
    def workspace(cls, workdir, es={}, index_prefix=None):
        """
        Create a workspace

        :param str workdir:
            The path to the directory where a git repository can
            be found or needs to be created when
            :py:meth:`.Workspace.setup` is called.
        :param dict es:
            The parameters to pass along to :func:`elasticutils.get_es`
        :param str index_prefix:
            The index_prefix use when generating index names for
            Elasticsearch
        :returns:
            :py:class:`.Workspace`
        """
        index_prefix = index_prefix or os.path.basename(workdir)
        repo = (cls.read_repo(workdir)
                if cls.is_repo(workdir)
                else cls.init_repo(workdir))
        return Workspace(repo, es, index_prefix)

    @classmethod
    def dot_git_path(cls, workdir):
        return os.path.join(workdir, '.git')

    @classmethod
    def is_repo(cls, workdir):
        return cls.is_dir(cls.dot_git_path(workdir))

    @classmethod
    def is_dir(cls, workdir):
        return os.path.isdir(workdir)

    @classmethod
    def read_repo(cls, workdir):
        return Repo(workdir)

    @classmethod
    def init_repo(cls, workdir, bare=False):
        return Repo.init(workdir, bare=bare)

    @classmethod
    def clone_repo(cls, repo_url, workdir):
        return Repo.clone_from(repo_url, workdir)

Q
F
