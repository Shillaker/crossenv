import subprocess

import pytest


def test_build_python_runs(build_python):
    out = build_python.run('--version', universal_newlines=True)
    assert out.strip() == 'Python %s' % build_python.version

def test_host_python_runs(host_python):
    out = host_python.run('--version', universal_newlines=True)
    assert out.strip() == 'Python %s' % host_python.version

def test_build_crossenv(build_python, host_python, tmpdir):
    out = build_python.run('-m', 'crossenv', '-vv',  host_python.exe,
            str(tmpdir))
