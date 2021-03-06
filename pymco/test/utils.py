"""
:py:mod:pymco.test.utils
------------------------
Utils for testing purposes.
"""
try:
    from unittest import mock
except ImportError:
    import mock  # noqa

import jinja2

from . import ctxt as _ctxt


def get_template(name, package=__package__):
    env = jinja2.Environment(loader=jinja2.PackageLoader(package, 'templates'))
    return env.get_template(name)


def configfile(ctxt=None):
    if not ctxt:
        ctxt = _ctxt.DEFAULT_CTXT
    with open(_ctxt.TEST_CFG, 'wt') as cfg:
        cfg.write(get_template('server.cfg.jinja').render({'config': ctxt}))
    return _ctxt.TEST_CFG
