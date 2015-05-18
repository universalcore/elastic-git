from zope.interface import Interface


class IStorageManager(Interface):

    def write_config(section, data):
        """
        Write a config block for a git repository.

        :param str section:
            The section to write the data for.
        :param dict data:
            The keys & values of data to write

        """

    def read_config(section):
        """
        Read a config block for a git repository.

        :param str section:
            The section to read.
        :returns: dict
        """

    def storage_exists():
        """
        Check if the storage exists. Returns ``True`` if the directory
        exists, it does not check if it is an actual :py:class:`git.Repo`.

        :returns: bool
        """

    def destroy_storage():
        """
        Destroy the repository's working dir.
        """

    def iterate(model_class):
        """
        This loads all known instances of this model from Git
        because we need to know how to re-populate Elasticsearch.

        :param elasticgit.models.Model model_class:
            The class to look for instances of.

        :returns: generator
        """

    def get(model_class, uuid):
        """
        Get a model instance by loading the data from git and constructing
        the model_class

        :param elasticgit.models.Model model_class:
            The model class of which an instance to return
        :param str uuid:
            The uuid for the object to retrieve
        :returns:
            :py:class:elasticgit.models.Model
        """

    def store(model, message, author=None, committer=None):
        """
        Store an instance's data in Git.

        :param elasticgit.models.Model model:
            The model instance
        :param str message:
            The commit message.
        :param tuple author:
            The author information (name, email address)
            Defaults repo default if unspecified.
        :param tuple committer:
            The committer information (name, email address).
            Defaults to the author if unspecified.
        :returns:
            The commit.
        """

    def store_data(repo_path, data, message,
                   author=None, committer=None):
        """
        Store some data in a file

        :param str repo_path:
            Where to store the file.
        :param obj data:
            The data to write in the file.
        :param str message:
            The commit message.
        :param tuple author:
            The author information (name, email address)
            Defaults repo default if unspecified.
        :param tuple committer:
            The committer information (name, email address).
            Defaults to the author if unspecified.
        :returns:
            The commit
        """

    def delete(model, message, author=None, committer=None):
        """
        Delete a model instance from Git.

        :param elasticgit.models.Model model:
            The model instance
        :param str message:
            The commit message.
        :param tuple author:
            The author information (name, email address)
            Defaults repo default if unspecified.
        :param tuple committer:
            The committer information (name, email address).
            Defaults to the author if unspecified.
        :returns:
            The commit.
        """

    def delete_data(repo_path, message,
                    author=None, committer=None):
        """
        Delete a file that's not necessarily a model file.

        :param str repo_path:
            Which file to delete.
        :param str message:
            The commit message.
        :param tuple author:
            The author information (name, email address)
            Defaults repo default if unspecified.
        :param tuple committer:
            The committer information (name, email address).
            Defaults to the author if unspecified.
        :returns:
            The commit
        """

    def pull(branch_name='master', remote_name='origin'):
        """
        Fetch & Merge in an upstream's commits.

        :param str branch_name:
            The name of the branch to fast forward & merge in
        :param str remote_name:
            The name of the remote to fetch from.
        """

    def path_info(path):
        """
        Analyze a file path and return the object's class and the uuid.

        :param str file_path:
            The path of the object we want a model instance for.
        :returns:
            (model_class, uuid) tuple or ``None`` if not a model file path.
        """
