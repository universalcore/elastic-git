# -*- coding: utf-8 -*-
import os
import pkg_resources

from elasticgit.tests.base import ToolBaseTest, TestPerson
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

    def test_introspection(self):
        workspace = self.mk_workspace()
        workspace.save(TestPerson({'age': 1, 'name': 'Foo'}), 'Saving.')
        shell = self.mk_shell(workspace.working_dir, introspect_models=True)
        [scope] = shell.args
        self.assertTrue('TestPerson' in scope)
        self.assertTrue('TestFallbackPerson' in scope)

    def test_introspection_off(self):
        workspace = self.mk_workspace()
        workspace.save(TestPerson({'age': 1, 'name': 'Foo'}), 'Saving.')
        shell = self.mk_shell(workspace.working_dir, introspect_models=False)
        [scope] = shell.args
        self.assertFalse('TestPerson' in scope)
        self.assertFalse('TestFallbackPerson' in scope)
