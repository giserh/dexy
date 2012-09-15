from dexy.plugins.process_filters import SubprocessFilter
from dexy.tests.utils import wrap
from dexy.doc import Doc

class NotPresentExecutable(SubprocessFilter):
    EXECUTABLE = 'notreal'

def test_not_present_executable():
    assert 'notreal' in NotPresentExecutable.executables()
    assert not NotPresentExecutable.executable()

def test_command_line_args():
    with wrap() as wrapper:
        doc = Doc("example.py|py",
                py={"args" : "-B"},
                wrapper=wrapper,
                contents="print 'hello'"
                )
        wrapper.docs = [doc]
        wrapper.run()

        assert doc.output().data() == "hello\n"

        command_used = doc.artifacts[-1].filter_instance.command_string()
        assert command_used == "python -B example.py  example.txt"

def test_scriptargs():
    with wrap() as wrapper:
        doc = Doc("example.py|py",
                py={"scriptargs" : "--foo"},
                wrapper=wrapper,
                contents="import sys\nprint sys.argv[1]"
                )
        wrapper.docs = [doc]
        wrapper.run()

        assert doc.output().data() == "--foo\n"

        command_used = doc.artifacts[-1].filter_instance.command_string()
        assert command_used == "python  example.py --foo example.txt"

def test_custom_env_in_args():
    with wrap() as wrapper:
        doc = Doc("example.py|py",
                py={"env" : {"FOO" : "bar" }},
                wrapper=wrapper,
                contents="import os\nprint os.environ['FOO']"
                )
        wrapper.docs = [doc]
        wrapper.run()

        assert doc.output().data() == "bar\n"