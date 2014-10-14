from elasticgit.commands.base import ToolCommand
from elasticgit import EG


class MigrateGitModelRepo(ToolCommand):

    command_name = 'migrate-gitmodel-repo'
    command_help_text = ('Migrate a GitModel based repository layout to an'
                         'Elastic-Git repository layout')
    command_arguments = (
        ('repo_url', 'The URL of the repository to migrate.'),
        ('working_dir', 'The directory to clone the repository in to.'),
    )

    def run(self, repo_url, working_dir):
        workspace = EG.workspace(working_dir)
        repo = workspace.repo
        repo.create_remote('gitmodel_remote', repo_url)
        remote = repo.remotes.gitmodel_remote
        [info] = remote.fetch()
        repo.git.merge(info.commit)
