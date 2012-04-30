import os
import logging
import getpass
import collections
import urlparse

import keyring

logger = logging.getLogger(__name__)

CredentialTuple = collections.namedtuple(
    'CredentialTuple', ['username', 'password']
)

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
        self.interactive = interactive
        self.max_tries = 1
        self._username = kwargs.get('username')
        self._password = kwargs.get('password')

    def success(self, username, password):
        """A method run after successful credential entry"""
        return

    def credentials(self):
        for i in range(self.max_tries):
            yield CredentialTuple(username=self._username, password=self._password)

class PromptFetcher(Fetcher):

    def __init__(self, value, uri, interactive, **kwargs):
        super(PromptFetcher, self).__init__(value, uri, interactive, **kwargs)
        self._cache = None
        self._tried_cache = False
        self.max_tries = 5

    def credentials(self):
        for i in range(self.max_tries):
            username, password = None, None
            if not self._tried_cache and self._cache:
                username, password = self._cache
                self._tried_cache = True
            if not (username and password):
                username = raw_input('Username for %s: ' % self.uri)
                password = getpass.getpass('Password for %s: ' % self.uri)
            yield CredentialTuple(username, password)


class PyPiRCFetcher(Fetcher):

    PYPIRC_LOC = '~/.pypirc'

    def __init__(self, value, uri, interactive, **kwargs):
        super(PyPiRCFetcher, self).__init__(value, uri, interactive, **kwargs)
        self.pypirc_loc = os.path.expanduser(
            kwargs.get('pypirc_loc', self.PYPIRC_LOC)
        )
        self._successful_config = None

    def credentials(self):
        if self._successful_config:
            yield self._successful_config

        config = self._get_pypirc_credentials()
        if config.has_key('repository'):
            netloc = lambda url: urlparse.urlparse(url)[1]
            if netloc(config.get('repository')) == netloc(self.uri):
                self._creds = CredentialTuple(
                    config.get('username'), config.get('password')
                )
                if self._creds.username and self._creds.password:
                    yield self._creds

    def success(self, username, password):
        if hasattr(self, '_creds'):
            self._successful_config = self._creds

    def _get_pypirc_credentials(self):
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

    def success(self, username, password):
        if getattr(self, '_no_keyring', False):
            return

        pw = self.SEP.join((username, password))
        try:
            keyring.set_password(self.SERVICE, self.uri, pw)
        except keyring.backend.PasswordSetError:
            logger.warning('Could not set password in keyring %s' % self.value)

    def _parse_credentials(self):
        pw = keyring.get_password(self.SERVICE, self.uri)
        if pw:
            self._username, self._password = pw.split(self.SEP)
        else:
            logger.warning('No password for %s in keyring %s' % (self.uri, self.value))

    def _configure_keyring(self):
        backend = keyring.core.load_keyring(None, 'keyring.backend.%s' % self.value)
        keyring.set_keyring(backend)
