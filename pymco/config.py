'''python-mcollective configuration module'''
import collections
import functools
import os

import six
from six.moves import configparser

from .connector import Connector
from .import exc
from .security import SecurityProvider
from .serializers import SerializerBase
from . import utils

INFINITE = 9999999999999999999


def lookup_with_default(fnc):
    '''
    Wraps ConfigParser lookups, catching exceptions and providing defaults.
    '''
    @functools.wraps(fnc)
    def decorator(self, name, *args, **kwargs):
        try:
            return fnc(self, name)
        except KeyError as exception:
            if 'default' in kwargs:
                return kwargs['default']
            raise exception
    return decorator


class Config(collections.Mapping):
    '''python-mcollective confiugration class.'''
    def __init__(self, configdict):
        self.config = configdict

    def __len__(self):
        return len(self.config)

    def __iter__(self):
        return six.iterkeys(self.config)

    def __getitem__(self, key):
        return self.config[key]

    @lookup_with_default
    def get(self, key):
        '''Get option by key.'''
        return self.__getitem__(key)

    @lookup_with_default
    def getint(self, key):
        '''Get int option by key.'''
        return int(self.__getitem__(key))

    @lookup_with_default
    def getfloat(self, key):
        '''Get float option by key.'''
        return float(self.__getitem__(key))

    @lookup_with_default
    def getboolean(self, key):
        '''Get bool option by key.'''
        value = self.__getitem__(key)
        if isinstance(value, six.string_types):
            if value.lower() in ('true', 'y', '1'):
                value = True
            else:
                value = False
            return bool(value)

    def get_connector(self):
        """Get connector based on MCollective settings."""
        import_path = Connector.plugins[self.config['connector']]
        return utils.import_object(import_path, config=self)

    def get_security(self):
        """Get security plugin based on MCollective settings."""
        import_path = SecurityProvider.plugins[self.config['securityprovider']]
        return utils.import_object(import_path, config=self)

    def get_serializer(self, key):
        """Get serializer based on MCollective settings."""
        import_path = SerializerBase.plugins[self.config[key]]
        return utils.import_object(import_path)

    def get_host_and_ports(self):
        """Get all hosts and port pairs for the current configuration.

        The result must follow the :py:class:`stomp.Connection`
        ``host_and_ports`` parameter.

        Returns:
            ``host_and_ports``: Iterable of two-tuple where the first element
            is the host and the second is the port.
        """
        if self.config['connector'] == 'stomp':
            return [(self.config['plugin.stomp.host'], self.getint('plugin.stomp.port'))]

        prefix = 'plugin.{connector}.pool.'.format(
            connector=self.config['connector'])
        host_key = prefix + '{index}.host'
        port_key = prefix + '{index}.port'
        host_and_ports = []

        for index in range(1, self.getint(prefix + 'size') + 1):
            host_and_ports.append((self.config[host_key.format(index=index)],
                                   self.getint(port_key.format(index=index))))

        return host_and_ports

    def get_user_and_password(self, current_host_and_port=None):
        """Get the user and password for the current host and port.

        Params:
            ``current_host_and_port``: two-tuple where the first element is the
            host and second is the port. This parameter is not required for
            ``stomp`` connector.

        Returns:
            ``user_and_password``: two-tuple where the first element is the
            user and the second is the password for the given host and port.
        Raises:
            :py:exc:`ValueError`: if connector isn't ``stomp`` and
            ``host_and_port`` is not provided.
            :py:exc:`pymco.exc.ConfigLookupError`: if host and port are not
            found into the connector list of host and ports.
        """
        connector = self.config['connector']
        if connector == 'stomp':
            return self.config['plugin.stomp.user'], self.config['plugin.stomp.password']
        elif current_host_and_port is None:
            raise ValueError('"host_and_port" parameter is required for {0} '
                             'connector'.format(connector))

        for index,  host_and_port in enumerate(self.get_host_and_ports(), 1):
            if host_and_port == current_host_and_port:
                prefix = 'plugin.{connector}.pool.'.format(
                    connector=self.config['connector'])
                user_key = prefix + '{index}.user'
                pass_key = prefix + '{index}.password'
                return (self.config[user_key.format(index=index)],
                        self.config[pass_key.format(index=index)])
        else:
            raise exc.ConfigLookupError(
                '{0} is not in the configuration for {1} connector'.format(
                    current_host_and_port, connector))

    def get_ssl_params(self):
        """Get SSL configuration for current connector

        Returns:
            ``ssl_params``: An iterable of SSL configuration parameters to be
            used with :py:meth:`stomp.Transport.set_ssl`.
        """
        connector = self.config['connector']
        if connector not in ('activemq', 'rabbitmq'):
            return ()

        params = []
        prefix = 'plugin.{0}.pool'.format(connector)
        for index in range(1, self.getint(prefix + '.size') + 1):
            current_prefix = '{prefix}.{index}'.format(prefix=prefix,
                                                       index=index)
            for_hosts = ((self.config.get(current_prefix + '.host'),
                          self.getint(current_prefix + '.port')),)
            current_prefix += '.ssl'
            if self.getboolean(current_prefix, default=False):
                params.append({
                    'for_hosts': for_hosts,
                    'cert_file': self.config.get(current_prefix + '.cert',
                                                 None),
                    'key_file': self.config.get(current_prefix + '.key', None),
                    'ca_certs': self.config.get(current_prefix + '.ca', None),
                })

        return params

    def get_ssl_parameters(self, current_host_and_port=None):
        """Get SSL parameters for the current host and port.

        Params:
            ``current_host_and_port``: two-tuple where the first element is the
            host and second is the port. This parameter is not required for
            ``stomp`` connector.

        Returns:
            ``ssl_parameters``: A dict-like object where eack key is a Stomp.py
            connection objcts SSL parameter.
        """
        connector = self.config['connector']
        if connector != 'activemq':
            raise ValueError('Only ActiveMQ connector support SSL parameters')

        prefix = 'plugin.activemq.pool.'
        params = {
            'use_ssl': False,
            'ssl_cert_file': None,
            'ssl_key_file': None,
            'ssl_ca_certs': None,
        }
        for index,  host_and_port in enumerate(self.get_host_and_ports(), 1):
            if host_and_port == current_host_and_port:
                prefix += '{index}.ssl'.format(index=index)
                params['use_ssl'] = self.getboolean(prefix, default=False)
                params['ssl_cert_file'] = self.config.get(prefix + '.cert', None)
                params['ssl_key_file'] = self.config.get(prefix + '.key', None)
                params['ssl_ca_certs'] = self.config.get(prefix + '.ca', None)

        return params

    def get_conn_params(self):
        """Get STOMP connection parameters for current configuration.

        Returns:
            ``params``: It will return a dictionary with stomp.py connection
            like key/values.
        """
        connector = self.config['connector']
        prefix = 'plugin.{0}.'.format(connector)

        if connector == 'stomp':
            return {'host_and_ports': self.get_host_and_ports()}

        return {
            'host_and_ports': self.get_host_and_ports(),
            'reconnect_sleep_initial':
            self.getfloat(prefix + 'initial_reconnect_delay', default=0.01),
            #'reconnect_sleep_increase': ,
            #'reconnect_sleep_jitter': ,
            'reconnect_sleep_max':
            self.getfloat(prefix + 'max_recconnect_delay', default=30.0),
            # Stomp gem, by default, try an infinite number of times
            # Stomp.py doesn't support it, so just use a really big number
            'reconnect_attempts_max':
            self.getfloat(prefix + 'max_recconect_attempts', default=INFINITE),
            'timeout':
            self.getfloat(prefix + 'timeout', default=None),
        }

    @staticmethod
    def from_configfile(configfile):
        '''Reads configfile and returns a new :py:class:`Config` instance'''
        configstr = open(configfile, 'rt').read()
        return Config.from_configstr(configstr)

    @staticmethod
    def from_configstr(configstr, section='default'):
        '''Parses given string an returns a new :py:class:`Config` instance'''
        config = six.StringIO()
        config.write('[{0}]\n'.format(section))
        config.write(configstr)
        config.seek(0, os.SEEK_SET)
        parser = configparser.ConfigParser()
        parser.readfp(config)
        return Config(dict(parser.items(section)))
