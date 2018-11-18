import os
import tarfile
import shutil
import subprocess

import requests
import pytest

_cache_dir = None

def pytest_configure(config):
    global _cache_dir
    _cache_dir = os.path.abspath(config.getini('cache_dir'))

@pytest.fixture(params=['3.7.0'])
def python_source(request, capsys):
    """Download the python source code"""
    root = 'Python-%s' % request.param
    dest = os.path.join(_cache_dir, root)
    tarball = dest + '.tar.xz'

    _download_source(request.param, tarball, capsys)
    _extract_tarball(tarball, dest, capsys)
    return dest


def _extract_tarball(tarball, dest, capsys):
    configure = os.path.join(dest, 'configure')

    if os.path.isfile(configure):
        return

    with tarfile.open(tarball) as tf:
        try:
            info = tf.getmember('%s/configure' % os.path.basename(dest))
        except KeyError:
            raise RuntimeError("Archive does not contain Python source")

        try:
            with capsys.disabled():
                print("\nExtracting %s..." % os.path.basename(tarball))
            tf.extractall(os.path.dirname(dest))
        except:
            try:
                shutil.rmtree(dest)
            except Exception:
                pass
            raise

def _download_source(version, tarball, capsys):
    if os.path.isfile(tarball):
        return

    url = 'https://www.python.org/ftp/python/%s/Python-%s.tar.xz' % (
            version, version)
    r = requests.get(url, stream=True)
    r.raise_for_status()
    try:
        with open(tarball, 'wb') as fp, capsys.disabled():
            print("\nDownloading Python %s..." % version)
            for chunk in r.iter_content(0x10000):
                fp.write(chunk)
    except:
        try:
            os.path.unlink(tarball)
        except OSError:
            pass
        raise


@pytest.fixture(scope='session')
def musl_host():
    """A musl-based toolchain that otherwise runs on the host. This is the
    easiest way to test."""
    pass
