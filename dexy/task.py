from dexy.plugin import PluginMeta
from dexy.utils import os_to_posix
import StringIO
import dexy.doc
import dexy.exceptions
import logging

class Task():
    ALIASES = []
    __metaclass__ = PluginMeta

    STATE_TRANSITIONS = [
            ('new', 'populating'),
            ('populating', 'populated'),
            ('populated', 'settingup'),
            ('settingup', 'setup'),
            ('setup', 'running'),
            ('running', 'complete'),

            # sometimes want to skip directly to populated
            ('new', 'populated')
            ]

    @classmethod
    def create(klass, alias, pattern, *children, **kwargs):
        task_class = klass.aliases[alias]
        return task_class(pattern, *children, **kwargs)

    def to_arg(self):
        alias = self.ALIASES[0]
        return "%s:%s" % (alias, self.key)

    def __repr__(self):
        return self.key_with_class()

    def __init__(self, key, *children, **args):
        self.key = os_to_posix(key)
        self.children = list(children)
        self.args = args

        self.created_by_doc = None
        self.deps = {}
        self.state = 'new'

        if args.has_key('wrapper') and args['wrapper']:
            self.wrapper = args['wrapper']

    def transition(self, to_state):
        if (self.state, to_state) in self.STATE_TRANSITIONS:
            self.state = to_state
        else:
            raise dexy.exceptions.InvalidStateTransition("%s => %s" % (self.state, to_state))

    def __iter__(self):
        def next_task():
            if self.state == 'new':
                self.transition('populating')
                yield self
                self.transition('populated')

            elif self.state == 'populated':
                self.transition('settingup')
                yield self
                self.transition('setup')

            elif self.state == 'setup':
                if self.wrapper.state == 'running':
                    self.transition('running')
                    yield self.pre
                    yield self
                    yield self.post
                    self.transition('complete')

            elif self.state in ('running', 'populating', 'settingup',):
                raise dexy.exceptions.CircularDependency

            elif self.state == 'complete':
                pass

            else:
                raise dexy.exceptions.UnexpectedState("%s in %s" % (self.state, self.key))

        return next_task()

    def __call__(self, *args, **kw):
        for child in self.children:
            for task in child:
                task(*args, **kw)

            self.deps[child.key_with_class()] = child
            self.deps.update(child.deps)

        if self.state == 'populating':
            self.populate()

        elif self.state == 'settingup':
            self.setup()
            self.wrapper.register(self)

        elif self.state == 'running':
            self.wrapper.db.add_task_before_running(self)
            self.run(*args, **kw)
            self.wrapper.db.update_task_after_running(self)

        else:
            raise dexy.exceptions.UnexpectedState("%s in %s" % (self.state, self.key))

    def setup(self):
        pass

    def run(self, *args, **kw):
        pass

    def populate(self):
        pass

    def pre(self, *args, **kw):
        pass

    def post(self, *args, **kw):
        pass

    def key_with_class(self):
        return "%s:%s" % (self.__class__.__name__, self.key)

    def key_with_batch_id(self):
        return "%s:%s:%s" % (self.wrapper.batch_id, self.__class__.__name__, self.key)

    def completed_child_docs(self):
        return [c for c in self.deps.values() if isinstance(c, dexy.doc.Doc) and c.state == 'complete']

    def setup_child_docs(self):
        return [c for c in self.deps.values() if isinstance(c, dexy.doc.Doc) and c.state in ('setup', 'complete',)]

    def set_log(self):
        self.log = logging.getLogger(self.key)
        self.logstream = StringIO.StringIO()
        handler = logging.StreamHandler(self.logstream)
        self.log.addHandler(handler)
        self.log.setLevel(logging.DEBUG)

        try:
            self.log.addHandler(logging.getLogger('dexy').handlers[0])
        except IndexError:
            pass
