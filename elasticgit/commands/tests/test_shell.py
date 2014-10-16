# -*- coding: utf-8 -*-
from elasticgit.tests.base import ToolBaseTest
from elasticgit.commands.shell import EGShell


class DummyShell(object):

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class TestDumpSchemaTool(ToolBaseTest):

    def mk_shell(self, *args, **kwargs):
        shell = EGShell(DummyShell)
        return shell.run(*args, **kwargs)

    def test_shell_workdir(self):
        shell = self.mk_shell('dir')
        [scope] = shell.args
        for var in ['Q', 'workspace', 'F', 'EG']:
            self.assertTrue(var in scope)

    def test_shell_models(self):
        shell = self.mk_shell('dir', 'elasticgit.tests.base')
        [scope] = shell.args
        for var in ['TestPerson', 'TestFallbackPerson']:
            self.assertTrue(var in scope)
