import os
import logging

import keyring

logger = logging.getLogger(__name__)

class Fetcher(object):
    """
    A class that can fetch http authentication credentials by some method.

    The credentials part will be defined by a URL, followed by a list of
    credentials fetching methods, each of which can have a buildout-style
    string passed to them, e.g.

    [pypi]
    uri = http://pypi.python.org
    use-aclfile = /tmp/people

    The "use-aclfile = /tmp/people" line would instantiate a use-aclfile
    fetcher, and pass it "/tmp/people" to its "value" kwarg. The fetcher would
    then return as many credentials as it could.
    """

    def __init__(self, value, uri, interactive, **kwargs):
        self.uri = uri
        self.value = value
        self._username = kwargs.get('username')
        self._password = kwargs.get('password')
        self._realm = kwargs.get('realm')

    def success(self, username, password, realm):
        """A method run after successful credential entry"""
        return

    @property
    def username(self):
        return self._username

    @property
    def password(self):
        return self._password

    @property
    def realm(self):
        return self._realm


class PyPiRCFetcher(Fetcher):

    PYPIRC_LOC = '~/.pypirc'

    def __init__(self, value, uri, interactive, **kwargs):
        super(PyPiRCFetcher, self).__init__(value, uri, interactive, **kwargs)
        self.pypirc_loc = os.path.expanduser(
            kwargs.get('pypirc_loc', self.PYPIRC_LOC)
        )
        self._config = self.get_pypirc_credentials()

    @property
    def username(self):
        return self._username or self._config.get('username')

    @property
    def password(self):
        return self._password or self._config.get('password')

    @property
    def realm(self):
        return self._realm or self._config.get('realm')

    def get_pypirc_credentials(self):
        """Acquire credentials from the user's pypirc file"""
        try:
            from distutils.dist import Distribution
            from distutils.config import PyPIRCCommand

            p = PyPIRCCommand(Distribution())

            p.repository = self.value
            p._get_rc_file = lambda: self.pypirc_loc

            return p._read_pypirc()
        except ImportError:
            return self.get_pypirc_py24()

    def _get_pypirc_py24():
        import ConfigParser

        config = {}
        c = ConfigParser.ConfigParser()

        if os.path.exists(self.pypirc_loc):
            c.read(self.pypirc_loc)
            config['username'] = c.get('server-login', 'username')
            config['password'] = c.get('server-login', 'password')

            repo = c.get('server-login', 'repository')
            if repo:
                config['repository'] = repo

        return config


class KeyringFetcher(Fetcher):
    """
    Uses python-keyring to securely fetch passwords from your keyring, if they
    exist. Degrades gracefully if the specified keyring doesn't exist.
    """

    SERVICE = 'isotoma.buildout.basicauth'
    SEP = ':|'

    def __init__(self, value, uri, interactive, **kwargs):
        super(KeyringFetcher, self).__init__(value, uri, interactive, **kwargs)
        self._configure_keyring()
        self._parse_credentials()

    def success(self, username, password, realm):
        if getattr(self, '_no_keyring', False):
            return

        pw = self.SEP.join((username, password, realm))
        try:
            keyring.set_password(self.SERVICE, self.uri, pw)
        except keyring.backend.PasswordSetError:
            logger.warning('Could not set password in keyring %s' % self.value)

    def _parse_credentials(self):
        pw = keyring.get_password(self.SERVICE, self.uri)
        if pw:
            self._username, self._password, self._realm = pw.split(self.SEP)
        else:
            logger.warning('No password for %s in keyring %s' % (self.uri, self.value))

    def _configure_keyring(self):
        backend = keyring.core.load_keyring(None, 'keyring.backend.%s' % self.value)
        keyring.set_keyring(backend)
