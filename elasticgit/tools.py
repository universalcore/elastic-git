import argparse

from elasticgit.commands.avro import SchemaDumper, SchemaLoader
from elasticgit.commands.gitmodel import MigrateGitModelRepo


def add_command(subparsers, dispatcher_class):  # pragma: no cover
    command = subparsers.add_parser(
        dispatcher_class.command_name,
        help=dispatcher_class.command_help_text)
    for argument, argument_help in dispatcher_class.command_arguments:
        command.add_argument(argument, help=argument_help)
    command.set_defaults(dispatcher=dispatcher_class)


def get_parser():  # pragma: no cover
    parser = argparse.ArgumentParser(
        description="Elasticgit command line tools.")
    subparsers = parser.add_subparsers(help='Commands')

    add_command(subparsers, SchemaDumper)
    add_command(subparsers, SchemaLoader)
    add_command(subparsers, MigrateGitModelRepo)

    return parser


if __name__ == '__main__':  # pragma: no cover
    parser = get_parser()
    args = parser.parse_args()
    data = vars(args)
    dispatcher_class = data.pop('dispatcher')
    dispatcher = dispatcher_class()
    dispatcher.run(**data)
