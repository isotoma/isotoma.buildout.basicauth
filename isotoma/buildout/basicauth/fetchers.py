import os

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

    def __init__(self, value, uri, **kwargs):
        self.uri = uri
        self.value = value
        self._username = kwargs.get('username')
        self._password = kwargs.get('password')
        self._realm = kwargs.get('realm')

    @property
    def username(self):
        return self._username

    @property
    def password(self):
        return self._password

    @property
    def realm(self):
        return self._realm

class PyPiFetcher(Fetcher):
    """Pull whatever credentials might be available out of the running user's
    pypirc config file. If an index_server argument is passed and the python
    version and packages support individual repositories, this class will fetch
    the credentials for the specified repository (falling back to
    "server-login")
    """

    PYPIRC_LOC = '~/.pypirc'

    def __init__(self, value, uri, **kwargs):
        super(PyPiFetcher, self).__init__(value, uri, **kwargs)
        self.pypirc_loc = os.path.expanduser(
            kwargs.get('pypirc_loc', self.PYPIRC_LOC)
        )
        self._config = self.get_pypirc_credentials()

    @property
    def username(self):
        if not self._username:
            return self._config.get('username', self._username)

    @property
    def password(self):
        if not self._password:
            return self._config.get('password', self._password)

    @property
    def realm(self):
        if not self._realm:
            return self._config.get('realm', self._realm)

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
