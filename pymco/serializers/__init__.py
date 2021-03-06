"""
py:mod:`pymco.serializers`
--------------------------
pymco Message [de]serialization.
"""
import abc


def serialize(self, msg):
    """Serialize a MCollective msg.

    Params:
        ``msg``: message to be serialized.
    Returns:
        ``msg``: serialized message.
    """


def deserialize(self, msg):
    """De-serialize a MCollective msg.

    Params:
        ``msg``: message to be de-serialized.
    Returns:
        ``msg``: de-serialized message.
    """

# Building Metaclass here for Python 2/3 compatibility
SerializerBase = abc.ABCMeta('SerializerBase', (object,), {
    'serialize': abc.abstractmethod(serialize),
    'deserialize': abc.abstractmethod(deserialize),
    'plugins': {
        'yaml': 'pymco.serializers.yaml.Serializer',
    }
})
