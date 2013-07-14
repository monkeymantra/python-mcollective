'''Tests for messaging objects.'''
import pytest

from pymco import exc
from pymco import message

from .. import base

def test_filter_add_cfclass(filter_):
    '''Tests :py:method:`pymco.message.Filter.add_class`.'''
    assert filter_.as_dict()['cf_class'] == []
    filter_.add_cfclass('common::linux')
    assert filter_.as_dict()['cf_class'] == ['common::linux']
    filter_.add_cfclass('apache')
    assert filter_.as_dict()['cf_class'] == ['common::linux', 'apache']


def test_filter_add_agent(filter_):
    '''Tests :py:method:`pymco.message.Filter.add_agent`.'''
    assert filter_.as_dict()['agent'] == []
    filter_.add_agent('package')
    assert filter_.as_dict()['agent'] == ['package']
    filter_.add_agent('registration')
    assert filter_.as_dict()['agent'] == ['package', 'registration']


def test_filter_add_fact(filter_):
    '''Tests :py:method:`pymco.message.Filter.add_fact` happy path.'''
    assert filter_.as_dict()['fact'] == []
    filter_.add_fact(fact='country', value='/uk/')
    assert filter_.as_dict()['fact'] == [{':fact': "country", ':value': "/uk/"}]
    filter_.add_fact(fact='country', value='/uk/', operator='==')
    assert filter_.as_dict()['fact'] == [
        {':fact': "country", ':value': "/uk/"},
        {':fact': "country", ':value': "/uk/", ':operator': '=='},
    ]


def test_filter_add_fact_operators(filter_):
    '''Tests :py:method:`pymco.message.Filter.add_fact` accepts only
    MCollective supported operators.'''
    for operator in ('==', '=~', '<=', '=>', '>=', '=<', '>', '<', '!='):
        filter_.add_fact(fact='country', value='/uk/', operator=operator)

    with pytest.raises(exc.BadFilterFactOperator):
        filter_.add_fact(fact='country', value='/uk/', operator='bad')


def test_filter_add_identity(filter_):
    '''Tests :py:method:`pymco.message.Filter.add_identity`.'''
    assert filter_.as_dict()['identity'] == []
    filter_.add_identity('foo.bar.com')
    assert filter_.as_dict()['identity'] == ['foo.bar.com']
    filter_.add_identity('spam.bar.com')
    assert filter_.as_dict()['identity'] == ['foo.bar.com', 'spam.bar.com']


def test_filter_method_chaining(filter_):
    '''Tests :py:class:`pymco.message.Filter` method chaining.'''
    assert filter_.as_dict() == { 'cf_class': [],
                                 'agent': [],
                                 'fact': [],
                                 'identity': [],
                                 }
    filter_.add_agent('package').add_identity('foo.bar.com')
    assert filter_.as_dict() == { 'cf_class': [],
                                 'agent': ['package'],
                                 'fact': [],
                                 'identity': ['foo.bar.com'],
                                 }


def test_message(msg, filter_):
    '''Tests :py:class:`pymco.message.Message` attribues.'''
    for name, value in (('senderid', 'mco1'),
                        ('msgtime', int(base.MSG['msgtime'])),
                        ('ttl', 60),
                        ('requestid', base.MSG['requestid']),
                        ('body', base.MSG['body']),
                        ('agent', base.MSG['agent']),
                        ('collective', 'mcollective'),
                        ('filter', filter_),
                        ):
        assert msg[name] == value


def test_message_length(msg):
    '''Tests :py:method:`pymco.message.Message.length`.'''
    assert len(msg) == len(msg._message)


def test_message_iteration(msg):
    '''Tests :py:method:`pymco.message.Message.__iter__`.'''
    assert sorted(list(msg)) == sorted(list(msg._message.keys()))


def test_message_raises_improperly_configured(config, filter_):
    '''Tests :py:class:`pymco.message.Message` raises
    :py:exc:`pymco.exc.ImproperlyConfigured` if configuration doesn't contain
    all required information.'''
    with pytest.raises(exc.ImproperlyConfigured):
        message.Message(body='ping',
                        agent='discovery',
                        config={},
                        filter_=filter_)


def test_message_set_item(msg):
    '''Tests :py:meth:`pymco.message.Message.__setitem__`.'''
    msg['test'] = 123
    assert msg['test'] == 123


def test_message_del_item(msg):
    '''Tests :py:meth:`pymco.message.Message.__delitem__`.'''
    msg['test'] = 123
    assert msg['test'] == 123
    del msg['test']
    with pytest.raises(KeyError):
        msg['test']
