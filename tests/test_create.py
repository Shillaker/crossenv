import subprocess

import pytest


def test_download(host_python):
    out = subprocess.check_output([host_python.exe, '--version'],
            universal_newlines=True)
    assert out.strip() == 'Python %s' % host_python.version
