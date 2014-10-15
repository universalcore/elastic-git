import sys


class ToolCommandError(Exception):
    pass


class ToolCommand(object):

    #: The name to assign to this on the command line
    command_name = None
    #: The help text for this command line, shown when called with ``--help``
    command_help_text = ''
    #: The arguments for this command's ``run()`` method
    command_arguments = ()

    #: Where the write the output to, override for testing.
    stdout = sys.stdout

    def run(self, **kwargs):  # pragma: no cover
        raise NotImplementedError('Subclasses are to implement this.')
