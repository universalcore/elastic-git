import sys


class ToolCommandError(Exception):
    pass


class CommandArgument(object):
    """
    Convenience wrapper for arguments to pass along to
    :py:func:`argparse.ArgumentParser.add_argument`
    """

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class ToolCommand(object):

    #: The name to assign to this on the command line
    command_name = None
    #: The help text for this command line, shown when called with ``--help``
    command_help_text = ''
    #: The :py:class:`CommandArgument`s for this command's
    #: ``run()`` method
    command_arguments = ()

    #: Where the write the output to, override for testing.
    stdout = sys.stdout

    def run(self, **kwargs):  # pragma: no cover
        raise NotImplementedError('Subclasses are to implement this.')
