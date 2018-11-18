import os
import tarfile
import shutil
import subprocess
from collections import namedtuple

import requests
import pytest

_cache_dir = None

_PythonInfo = namedtuple('PythonInfo',
        'version source build install exe')
_NullInfo = _PythonInfo(None, None, None, None, None)

def PythonInfo(**kwargs):
    return _NullInfo._replace(**kwargs)

def pytest_configure(config):
    global _cache_dir
    _cache_dir = os.path.abspath(config.getini('cache_dir'))


class _speak():
    def __init__(self, capsys):
        self.capsys = capsys
        self.first = True

    def __call__(self, *args, **kwargs):
        with self.capsys.disabled():
            if self.first:
                print('\n')
                self.first = False
            print(*args, **kwargs)

    def __enter__(self):
        self.capsys.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.capsys.__exit__(exc_type, exc_val, exc_tb)
        
@pytest.fixture
def speak(capsys):
    return _speak(capsys)

@pytest.fixture(params=['3.7.0'])
def python_source(request, speak):
    """Download the python source code"""
    root = 'Python-%s' % request.param
    dest = os.path.join(_cache_dir, root)
    tarball = dest + '.tar.xz'

    _download_source(request.param, tarball, speak)
    _extract_tarball(tarball, dest, speak)
    return PythonInfo(version=request.param, source=dest)


def _extract_tarball(tarball, dest, speak):
    configure = os.path.join(dest, 'configure')

    if os.path.isfile(configure):
        return

    with tarfile.open(tarball) as tf:
        try:
            info = tf.getmember('%s/configure' % os.path.basename(dest))
        except KeyError:
            raise RuntimeError("Archive does not contain Python source")

        try:
            speak("Extracting %s..." % os.path.basename(tarball))
            tf.extractall(os.path.dirname(dest))
        except:
            try:
                shutil.rmtree(dest)
            except Exception:
                pass
            raise

def _download_source(version, tarball, speak):
    if os.path.isfile(tarball):
        return

    url = 'https://www.python.org/ftp/python/%s/Python-%s.tar.xz' % (
            version, version)
    r = requests.get(url, stream=True)
    r.raise_for_status()
    try:
        os.makedirs(os.path.dirname(tarball), exist_ok=True)
        with open(tarball, 'wb') as fp:
            speak("Downloading Python %s..." % version)
            for chunk in r.iter_content(0x10000):
                fp.write(chunk)
    except:
        try:
            os.unlink(tarball)
        except OSError:
            pass
        raise

def _run_command(*args, error=None, **kwargs):
    try:
        subprocess.check_call(args, **kwargs)
    except (subprocess.CalledProcessError, OSError) as e:
        if error is not None:
            raise RuntimeError(error) from None
        raise

@pytest.fixture(params=['installed', 'uninstalled'])
def host_python(request, python_source, speak):
    working_dir = python_source.source + '-build'
    install_dir = python_source.source + '-install'
    working_py = os.path.join(working_dir, 'python')
    install_py = os.path.join(install_dir, 'bin', 'python3')
    configure = os.path.join(python_source.source, 'configure')

    if not os.path.isfile(working_py) or not os.path.isfile(install_py):
        speak("Building Python %s" % python_source.version)
        os.makedirs(working_dir, exist_ok=True)
        _run_command(configure, '--prefix='+install_dir, cwd=working_dir)
        _run_command('make', cwd=working_dir) # TODO: parallel
        _run_command('make', 'install', cwd=working_dir)

    if request.param == 'installed':
        exe = install_py
    else:
        exe = working_py

    return python_source._replace(build=working_dir, install=install_dir,
            exe=exe)

@pytest.fixture(scope='session')
def musl_host():
    """A musl-based toolchain that otherwise runs on the host. This is the
    easiest way to test."""
    pass
