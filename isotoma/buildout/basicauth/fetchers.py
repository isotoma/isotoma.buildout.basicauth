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
            yield (username, password, True)


class PyPiRCFetcher(Fetcher):

    name = "pypi"
    PYPIRC_LOC = '~/.pypirc'

    def __init__(self, mgr):
        super(PyPiRCFetcher, self).__init__(mgr)
        self.pypirc_loc = os.path.expanduser(self.PYPIRC_LOC)
        self.config = self._get_pypirc_credentials()

    def search(self, uri, realm):
        for realm, username, password in self.config:
            if uri.startswith(realm):
                yield username, password, True

    def _get_pypirc_credentials(self):
        if not os.path.exists(self.pypirc_loc):
            return []

        config = []

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
            try:
                uri = c.get(section, 'repository')
                username = c.get(section, 'username')
                password = c.get(section, 'password')
            except ConfigParser.NoOptionError:
                continue
            config.append((uri, username, password))

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
            username, password = pw.split(self.SEP)
            yield username, password, True


class LovelyFetcher(Fetcher):

    name = "lovely"

    def search(self, uri, realm):
        lovely = self.mgr.buildout.get("lovely.buildouthttp", {})
        lovely_uri = lovely.get("uri", None)
        if lovely_uri and uri.startswith(lovely_uri):
            username = lovely.get("username", None)
            password = lovely.get("password", None)
            if username and password:
                yield username, password, True


class BuildoutFetcher(Fetcher):

    name = "buildout"


    def __init__(self, mgr):
        super(BuildoutFetcher, self).__init__(mgr)
        self.creds = []

        if not "basicauth" in self.mgr.buildout:
            return

        basicauth = self.mgr.buildout["basicauth"]
        if "credentials" in basicauth:
            for partname in basicauth.get_list("credentials"):
                part = self.mgr.buildout[partname]
                self.creds.append((part["uri"], part["username"], part["password"]))


    def search(self, uri, realm):
        for repo_uri, username, password in self.creds:
            if uri.startswith(repo_uri):
                yield username, password, True

