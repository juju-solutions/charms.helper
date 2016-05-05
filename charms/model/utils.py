
import os
import copy
import json
import yaml

from functools import wraps
from collections import UserDict

cache = {}
MARKER = object()


def charm_dir():
    """Return the root directory of the current charm"""
    return os.environ.get('CHARM_DIR')


def atexit(callback, *args, **kwargs):
    '''Schedule a callback to run on successful hook completion.

    Callbacks are run in the reverse order that they were added.'''
    _atexit.append((callback, args, kwargs))


def cached(func):
    """Cache return values for multiple executions of func + args

    For example::

        @cached
        def unit_get(attribute):
            pass

        unit_get('test')

    will cache the result of unit_get + 'test' for future calls.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        global cache
        key = str((func, args, kwargs))
        try:
            return cache[key]
        except KeyError:
            pass  # Drop out of the exception handler scope.
        res = func(*args, **kwargs)
        cache[key] = res
        return res
    wrapper._wrapped = func
    return wrapper


def flush(key):
    """Flushes any entries from function cache where the
    key is found in the function+args """
    flush_list = []
    for item in cache:
        if key in item:
            flush_list.append(item)
    for item in flush_list:
        del cache[item]


class Serializable(UserDict):
    """Wrapper, an object that can be serialized to yaml or json"""

    def __init__(self, obj):
        # wrap the object
        UserDict.__init__(self)
        self.data = obj

    def __getattr__(self, attr):
        # See if this object has attribute.
        if attr in ("json", "yaml", "data"):
            return self.__dict__[attr]
        # Check for attribute in wrapped object.
        got = getattr(self.data, attr, MARKER)
        if got is not MARKER:
            return got
        # Proxy to the wrapped object via dict interface.
        try:
            return self.data[attr]
        except KeyError:
            raise AttributeError(attr)

    def __getstate__(self):
        # Pickle as a standard dictionary.
        return self.data

    def __setstate__(self, state):
        # Unpickle into our wrapper.
        self.data = state

    def json(self):
        """Serialize the object to json"""
        return json.dumps(self.data)

    def yaml(self):
        """Serialize the object to yaml"""
        return yaml.dump(self.data)


class Config(dict):
    """A dictionary representation of the charm's config.yaml, with some
    extra features:

    - See which values in the dictionary have changed since the previous hook.
    - For values that have changed, see what the previous value was.
    - Store arbitrary data for use in a later hook.

    NOTE: Do not instantiate this object directly - instead call
    ``hookenv.config()``, which will return an instance of :class:`Config`.

    Example usage::

        >>> # inside a hook
        >>> from charmhelpers.core import hookenv
        >>> config = hookenv.config()
        >>> config['foo']
        'bar'
        >>> # store a new key/value for later use
        >>> config['mykey'] = 'myval'


        >>> # user runs `juju set mycharm foo=baz`
        >>> # now we're inside subsequent config-changed hook
        >>> config = hookenv.config()
        >>> config['foo']
        'baz'
        >>> # test to see if this val has changed since last hook
        >>> config.changed('foo')
        True
        >>> # what was the previous value?
        >>> config.previous('foo')
        'bar'
        >>> # keys/values that we add are preserved across hooks
        >>> config['mykey']
        'myval'

    """
    CONFIG_FILE_NAME = '.juju-persistent-config'

    def __init__(self, *args, **kw):
        super(Config, self).__init__(*args, **kw)
        self.implicit_save = True
        self._prev_dict = None
        self.path = os.path.join(charm_dir(), Config.CONFIG_FILE_NAME)
        if os.path.exists(self.path):
            self.load_previous()
        atexit(self._implicit_save)

    def load_previous(self, path=None):
        """Load previous copy of config from disk.

        In normal usage you don't need to call this method directly - it
        is called automatically at object initialization.

        :param path:

            File path from which to load the previous config. If `None`,
            config is loaded from the default location. If `path` is
            specified, subsequent `save()` calls will write to the same
            path.

        """
        self.path = path or self.path
        with open(self.path) as f:
            self._prev_dict = json.load(f)
        for k, v in copy.deepcopy(self._prev_dict).items():
            if k not in self:
                self[k] = v

    def changed(self, key):
        """Return True if the current value for this key is different from
        the previous value.

        """
        if self._prev_dict is None:
            return True
        return self.previous(key) != self.get(key)

    def previous(self, key):
        """Return previous value for this key, or None if there
        is no previous value.

        """
        if self._prev_dict:
            return self._prev_dict.get(key)
        return None

    def save(self):
        """Save this config to disk.

        If the charm is using the :mod:`Services Framework <services.base>`
        or :meth:'@hook <Hooks.hook>' decorator, this
        is called automatically at the end of successful hook execution.
        Otherwise, it should be called directly by user code.

        To disable automatic saves, set ``implicit_save=False`` on this
        instance.

        """
        with open(self.path, 'w') as f:
            json.dump(self, f)

    def _implicit_save(self):
        if self.implicit_save:
            self.save()
