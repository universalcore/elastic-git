from confmodel.config import ConfigMetaClass

from elasticgit.commands.base import ToolCommand, CommandArgument
from elasticgit import EG, F, Q
from elasticgit.utils import load_class

try:
    from IPython import start_ipython

    def default_launcher(scope):
        return start_ipython(argv=[], user_ns=scope)

except ImportError:
    def default_launcher(scope):
        import code
        import readline
        import rlcompleter
        readline.set_completer(
            rlcompleter.Completer(scope).complete)
        readline.parse_and_bind("tab:complete")
        code.interact(local=scope)


class EGShell(ToolCommand):
    """
    Fire up a :py:class:`elasticgit.manager.Workspace` instance
    for debugging straight from the command line.

    Sets the following variables in the local scope:

    - ``workspace``, a :py:class:`elasticgit.manager.Workspace` pointing
      at the working directory provided.
    - ``Q``, ``F`` and ``EG`` already imported
    - all models loaded from the model class path provided.

    Uses IPython if installed.

    ::

        python -m elasticgit.tools shell ./repo -m elasticgit.tests.base
        Python 2.7.6 (default, Dec 22 2013, 09:30:03)
        [GCC 4.2.1 Compatible Apple LLVM 5.0 (clang-500.2.79)] on darwin
        Type "help", "copyright", "credits" or "license" for more information.
        (InteractiveConsole)
        >>> workspace.S(TestPerson).count()
        0
        >>>

    """
    command_name = 'shell'
    command_help_text = (
        'Load a repo and make an EG workspace available for debugging')
    command_arguments = (
        CommandArgument(
            'workdir',
            metavar='workdir',
            help='Path to the repository\'s working directory.'),
        CommandArgument(
            '-m', '--models',
            dest='models',
            help='The models file to load.')
    )

    def __init__(self, launcher=None):
        self.launcher = launcher

    def run(self, workdir, models):
        namespace = {}
        if models is not None:
            models_module = load_class(models)
            models = dict([
                (name, value)
                for name, value in models_module.__dict__.items()
                if isinstance(value, ConfigMetaClass)
            ])
            namespace.update(models)

        namespace.update({
            'workspace': EG.workspace(workdir),
            'Q': Q,
            'EG': EG,
            'F': F,
        })

        launcher = self.launcher or default_launcher
        return launcher(namespace)
