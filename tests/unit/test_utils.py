from types import SimpleNamespace
import os
import subprocess

import pytest

import crossenv.utils

def test_FormatMapping():
    ns = SimpleNamespace(
            foo=1,
            bar=SimpleNamespace(
                baz=2,
                spam='abc',
                ),
            )
    objs = {'a': 1, 'b': 2, 'c': ns}
    mapping = crossenv.utils.FormatMapping(objs)
    assert mapping['a'] == 1
    assert mapping['b'] == 2
    assert mapping['c'] is ns
    assert mapping['c.foo'] == 1
    assert mapping['c.bar'] is ns.bar
    assert mapping['c.bar.baz'] == 2
    assert mapping['c.bar.spam'] == 'abc'
    with pytest.raises(KeyError):
        mapping['x']
    with pytest.raises(AttributeError):
        mapping['a.foo']
    with pytest.raises(AttributeError):
        mapping['c.qqq']

def test_F():
    local1 = 1
    local2 = 'foobar'
    ns = SimpleNamespace(
            foo=1,
            bar=SimpleNamespace(
                baz=2,
                spam='abc',
                ),
            )

    context = {'a': local1, 'b': local2, 'c': ns}
    assert crossenv.utils.F('%(a)2d', context) == ' 1'
    assert crossenv.utils.F('%(a).3f', context) == '1.000'
    assert crossenv.utils.F('%(b)-10s', context) == 'foobar    '
    assert crossenv.utils.F('%(c.foo)2d', context) == ' 1'
    assert crossenv.utils.F('%(c.bar.baz).3f', context) == '2.000'
    assert crossenv.utils.F('%(c.bar.spam)-10s', context) == 'abc       '
    with pytest.raises(AttributeError):
        crossenv.utils.F('%(c.blah)', context)

    assert crossenv.utils.F('%(local1)2d', locals()) == ' 1'
    assert crossenv.utils.F('%(local1).3f', locals()) == '1.000'
    assert crossenv.utils.F('%(local2)-10s', locals()) == 'foobar    '
    assert crossenv.utils.F('%(ns.foo)2d', locals()) == ' 1'
    assert crossenv.utils.F('%(ns.bar.baz).3f', locals()) == '2.000'
    assert crossenv.utils.F('%(ns.bar.spam)-10s', locals()) == 'abc       '
    with pytest.raises(AttributeError):
        crossenv.utils.F('%(ns.blah)', locals())


def put_file(path, value):
    with open(path, 'w') as fp:
        fp.write(value)

def get_file(path):
    with open(path, 'r') as fp:
        return fp.read()

def test_overwrite_file(tmpdir):
    file1 = str(tmpdir.join('file1'))
    put_file(file1, 'original')
    with crossenv.utils.overwrite_file(file1) as fp:
        fp.write('replacement')
    assert get_file(file1) == 'replacement'

    file2 = str(tmpdir.join('file2'))
    put_file(file2, 'original')
    try:
        with crossenv.utils.overwrite_file(file2) as fp:
            fp.write('replacement')
            fp.flush()
            raise IndexError("oh no!")
    except IndexError:
        pass
    assert get_file(file2) == 'original'

def test_overwrite_file_mode(tmpdir):
    file1 = str(tmpdir.join('file1'))
    put_file(file1, 'original')
    with crossenv.utils.overwrite_file(file1, 'w+b') as fp:
        fp.write(b'replacement')
        fp.flush()
        fp.seek(0)
        fp.write(b'!')
        fp.seek(0)
        assert fp.read() == b'!eplacement'
    assert get_file(file1) == '!eplacement'

def test_overwrite_file_perms(tmpdir):
    file1 = str(tmpdir.join('file1'))
    put_file(file1, 'original')
    os.chmod(file1, 0o775)
    with crossenv.utils.overwrite_file(file1, perms=0o600) as fp:
        fp.write('replacement')
    assert get_file(file1) == 'replacement'
    assert os.stat(file1).st_mode & 0o777 == 0o600

def test_mkdir_if_needed(tmpdir):
    dir1 = str(tmpdir.join('dir1'))
    assert not os.path.isdir(dir1)
    crossenv.utils.mkdir_if_needed(dir1)
    assert os.path.isdir(dir1)
    crossenv.utils.mkdir_if_needed(dir1) # No error

    file1 = str(tmpdir.join('file1'))
    put_file(file1, 'foobar')
    with pytest.raises(ValueError):
        crossenv.utils.mkdir_if_needed(file1)

    link1 = str(tmpdir.join('link1'))
    os.symlink(dir1, link1)
    with pytest.raises(ValueError):
        crossenv.utils.mkdir_if_needed(link1)

def remove_path(tmpdir):
    dir1 = str(tmpdir.join('dir1'))
    file1 = str(tmpdir.join('file1'))
    file2 = str(tmpdir.join('dir1', 'file2'))
    link1 = str(tmpdir.join('link1'))
    os.mkdidr(dir1)
    put_file(file1, 'abc')
    put_file(file2, 'def')
    os.symlink(dir1, link1)

    assert os.path.exists(link1)
    assert os.path.isdir(dir1)
    crossenv.utils.remove_path(link1)
    assert not os.path.exists(link1)
    assert os.path.isdir(dir1)

    assert os.path.isfile(file1)
    crossenv.utils.remove_path(file1)
    assert not os.path.exists(file1)

    assert os.path.isdir(dir2)
    crossenv.utils.remove_path(dir2)
    assert not os.path.exists(file1)

def test_symlink(tmpdir):
    file1 = str(tmpdir.join('file1'))
    file2 = str(tmpdir.join('file2'))
    link1 = str(tmpdir.join('link1'))
    link2 = str(tmpdir.join('link2'))
    put_file(file1, 'abc')
    put_file(file2, 'def')
    os.symlink(file1, link1)

    assert get_file(link1) == 'abc'
    crossenv.utils.symlink(file2, link1)
    assert get_file(link1) == 'def'

    crossenv.utils.symlink(file1, link2)
    assert get_file(link2) == 'abc'

def run_command(*cmd):
    out = subprocess.check_output(cmd, universal_newlines=True)
    return out.strip()

def test_make_launcher(tmpdir):
    script = str(tmpdir.join('script'))
    script2 = str(tmpdir.join('script2'))

    with open(script, 'w') as fp:
        fp.write('#!/bin/sh\n')
        fp.write('echo foo "$@"\n')
    os.chmod(script, 0o700)
    assert run_command(script, 'a', 'b') == 'foo a b'

    crossenv.utils.make_launcher(script, script2)
    assert not os.path.islink(script2)
    assert run_command(script2, 'a', 'b') == 'foo a b'

def test_install_script(tmpdir):
    # This one doesn't test that much...
    MARKER = 1234 # Works with %d, %f, %s, %r
    class FakeLocals:
        def __getitem__(self, key):
            return self
        def __getattr__(self, name):
            return MARKER
    script = str(tmpdir.join('script'))
    crossenv.utils.install_script('site.py.tmpl', script, FakeLocals(),
            0o741)
    assert os.path.isfile(script)
    assert os.stat(script).st_mode & 0o777 == 0o741
    count = 0
    with open(script) as fp:
        for line in fp:
            if str(MARKER) in line:
                count += 1
    assert count > 0 
