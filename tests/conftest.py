import sys
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

class PythonSource:
    URL = 'https://www.python.org/ftp/python/%s/Python-%s.tar.xz'

    """Download and unpack a Python version"""
    def __init__(self, version):
        self.version = version
        self.url = self.URL % (version, version)
        basename = self.url.rsplit('/',1)[-1]
        self.tarball = os.path.join(_cache_dir, basename)
        self.extracted = os.path.join(_cache_dir, 'Python-' + self.version)
        self.configure = os.path.join(self.extracted, 'configure')
        self._download()
        self._extract()

    def _download(self):
        if os.path.isfile(self.tarball):
            return

        print("Downloading Python %s" % self.version)
        r = requests.get(self.url, stream=True)
        r.raise_for_status()
        try:
            os.makedirs(os.path.dirname(self.tarball), exist_ok=True)
            with open(self.tarball, 'wb') as fp:
                for chunk in r.iter_content(0x10000):
                    fp.write(chunk)
        except:
            try:
                os.unlink(self.tarball)
            except OSError:
                pass
            raise


    def _extract(self):
        if os.path.isfile(self.configure):
            return

        print("Extracting %s" % os.path.basename(self.tarball))

        with tarfile.open(self.tarball) as tf:
            extract_dir = os.path.dirname(self.extracted)
            try:
                configure = os.path.relpath(self.configure, extract_dir)
                info = tf.getmember(configure)
            except KeyError:
                raise RuntimeError("Archive does not contain Python source")

            try:
                tf.extractall(extract_dir)
            except:
                try:
                    shutil.rmtree(self.extracted)
                except Exception:
                    pass
                raise

class MakePython:
    """A class for building python from source"""
    def __init__(self, version, tag='build',
            source=None, working=None, install=None,
            config_args=None, make_env=None, make_args=None):
        self.version = version
        self.tag = tag

        if source is None:
            self.source = PythonSource(version)
        else:
            self.source = source

        if working is None:
            self.working = '-'.join([self.source.extracted, self.tag])
        else:
            self.working = working
        self.makefile = os.path.join(self.working, 'Makefile')

        if install is None:
            self.install = self.working + '-install'
        else:
            self.install = install

        self.config_args = config_args or []
        self.make_env = make_env or {}
        self.make_args = make_args or []

        self.working_exe = os.path.join(self.working, 'python')
        self.install_exe = os.path.join(self.install, 'bin', 'python3')
        self._build()

    def _build(self):
        if (os.path.isfile(self.working_exe) and
                os.path.isfile(self.install_exe)):
            return

        os.makedirs(self.working, exist_ok=True)
        cmdline = [ self.source.configure, '--prefix=' + self.install ]
        cmdline.extend(self.config_args)
        subprocess.check_call(cmdline, cwd=self.working)

        cmdline = [ 'make' ]
        cmdline.extend(self.make_args)
        env = os.environ.copy()
        env.update(self.make_env)
        subprocess.check_call(cmdline, cwd=self.working, env=env)

        cmdline = [ 'make', 'install' ]
        cmdline.extend(self.make_args)
        env = os.environ.copy()
        env.update(self.make_env)
        subprocess.check_call(cmdline, cwd=self.working, env=env)


class RunPythonBase:
    # Need self.version, self.exe
    def run(self, *args, **kwargs):
        cmdline = [ self.exe ]
        cmdline.extend(args)
        return subprocess.check_output(cmdline, **kwargs)

class RunPython(RunPythonBase):
    def __init__(self, version, installed=True):
        self.version = version
        self.make = MakePython(version)
        self.source = self.make.source
        if installed:
            self.exe = self.make.install_exe
        else:
            self.exe = self.make.working_exe


class SystemPython(RunPythonBase):
    def __init__(self):
        self.exe = sys.executable
        self.version = sys.version.split()[0]


class NativeHostPython(RunPythonBase):
    """Here the host and build pythons are the same. This is for
    quick tests of basic functionality."""
    def __init__(self, build_python):
        self.version = build_python.version
        self.exe = build_python.exe


@pytest.fixture(params=['system', '3.7.0'])
def build_python(request, capsys):
    with capsys.disabled(): # Want 'downloading... notifications'
        if request.param == 'system':
            return SystemPython()
        else:
            return RunPython(request.param)


@pytest.fixture(params=['native'])
def host_python(request, build_python, capsys):
    with capsys.disabled():
        if request.param == 'native':
            return NativeHostPython(build_python)
        else:
            raise NotImplementedError("TODO: %s" % request.param)
