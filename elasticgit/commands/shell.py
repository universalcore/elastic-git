import os

from elasticgit.commands.base import ToolCommand, CommandArgument
from elasticgit.commands.utils import load_models
from elasticgit import EG, F, Q

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
    Fire up a :py:class:`elasticgit.workspace.Workspace` instance
    for debugging straight from the command line.

    Sets the following variables in the local scope:

    - ``workspace``, a :py:class:`elasticgit.workspace.Workspace` pointing
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
        >>> workspace.S(TestPerson).count()  # doctest: +SKIP
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
            help='The models module to load.'),
        CommandArgument(
            '-n', '--no-introspect-models',
            dest='introspect_models',
            help='Do not find & load models automatically.',
            default=True, action='store_false')
    )

    def __init__(self, launcher=None):
        self.launcher = launcher

    def run(self, workdir, models=None, introspect_models=None):
        namespace = {}
        if models is not None:
            namespace.update(load_models(models))

        if introspect_models:
            possible_models = [m for m in os.listdir(workdir)
                               if os.path.isdir(os.path.join(workdir, m))
                               and not m.startswith('.')]
            for models in possible_models:
                try:
                    found_models = load_models(models)
                    namespace.update(found_models)
                except ValueError:
                    print '%s does not look like a models module.' % (models,)

        namespace.update({
            'workspace': EG.workspace(workdir),
            'Q': Q,
            'EG': EG,
            'F': F,
        })

        launcher = self.launcher or default_launcher
        return launcher(namespace)
