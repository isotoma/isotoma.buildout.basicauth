import os
import logging
import getpass
import urlparse
import ConfigParser

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

    def __init__(self, mgr):
        self.mgr = mgr

    def success(self, uri, username, password):
        """A method run after successful credential entry"""
        return

    def search(self, uri, realm):
        raise StopIteration


class PromptFetcher(Fetcher):

    name = "prompt"

    def __init__(self, mgr):
        super(PromptFetcher, self).__init__(mgr)
        self.max_tries = 5

    def search(self, uri, realm):
        if not self.mgr.interactive:
            raise StopIteration

        for i in range(self.max_tries):
            username = raw_input('Username for %s: ' % realm)
            password = getpass.getpass('Password for %s: ' % realm)
            yield (username, password)


class PyPiRCFetcher(Fetcher):

    name = "pypi"
    PYPIRC_LOC = '~/.pypirc'

    def __init__(self, mgr):
        super(PyPiRCFetcher, self).__init__(mgr)
        self.pypirc_loc = os.path.expanduser(self.PYPIRC_LOC)
        self.config = self._get_pypirc_credentials()

    def search(self, uri, realm):
        if uri in self.config:
            yield self.config[uri]

    def _get_pypirc_credentials(self):
        if not os.path.exists(self.pypirc_loc):
            return

        config = {}

        c = ConfigParser.ConfigParser()
        c.read(self.pypirc_loc)

        idx = []

        if c.has_section("server-login"):
            idx.append("server-login")

        if c.has_section("distutils"):
            for section in c.get("distutils", "index-servers").split("\n"):
                section = section.strip()
                if not section:
                    continue
                idx.append(section)

        for section in idx:
            uri = c.get('server-login', 'repository')
            username = c.get(section, 'username')
            password = c.get(section, 'password')
            if not uri or not username or not password:
                continue
            config[uri] = (username, password)

        return config


class KeyringFetcher(Fetcher):
    """
    Uses python-keyring to securely fetch passwords from your keyring, if they
    exist. Degrades gracefully if the specified keyring doesn't exist.
    """

    name = "keyring"
    SERVICE = 'isotoma.buildout.basicauth'
    SEP = ':|'

    def __init__(self, mgr):
       super(KeyringFetcher, self).__init__(mgr)
       backend = keyring.core.load_keyring(None, 'keyring.backend.%s' % "GnomeKeyring")
       keyring.set_keyring(backend)

    def success(self, uri, username, password):
        pw = self.SEP.join((username, password))
        try:
            keyring.set_password(self.SERVICE, uri, pw)
        except keyring.backend.PasswordSetError:
            logger.warning('Could not set password in keyring')

    def search(self, uri, realm):
        pw = keyring.get_password(self.SERVICE, realm)
        if pw:
            yield pw.split(self.SEP)


class LovelyFetcher(Fetcher):

    name = "lovely"

    def search(self, uri, realm):
        lovely = self.mgr.buildout.get("lovely.buildouthttp", {})
        lovely_uri = lovely.get("uri", None)
        if lovely_uri and uri.startswith(lovely_uri):
            username = lovely.get("username", None)
            password = lovely.get("password", None)
            yield username, password


class BuildoutFetcher(Fetcher):

    name = "buildout"

    def search(self, uri, realm):
        basicauth = self.mgr.buildout["basicauth"]
        if "credentials" in basicauth:
            for partname in basicauth.get_list("credentials"):
                part = self.mgr.buildout[partname]
                if uri.startswith(part["uri"]):
                    yield part["username"], part["password"]


