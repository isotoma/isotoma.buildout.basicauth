from isotoma.buildout.basicauth.fetchers import PyPiRCFetcher

class Credentials(object):
    """
    A class to instantiate then iterate over `Fetcher`s to acquire a full set
    of credentials for a particular URI.
    """

    AVAILABLE_FETCHERS = {
        'use-pypirc': PyPiRCFetcher,
    }

    def __init__(self, uri, fetch_using=[], **kwargs):
        self._uri = uri
        self._username = kwargs.get('username')
        self._password = kwargs.get('password')
        self._realm = kwargs.get('realm')
        self._fetch_using = fetch_using

    @property
    def username(self):
        return self._username

    @property
    def password(self):
        return self._password

    @property
    def realm(self):
        return self._realm

    @property
    def uri(self):
        return self._uri

    def required_credentials(self):
        required = []

        if not self._username:
            required.append('username')

        if not self._password:
            required.append('password')

        if not self._realm:
            required.append('realm')

        return required

    def get_credentials(self):
        """Iterate across all of the available fetchers until we acquire all of
        the credentials we require"""

        for fetcher, value in self._fetch_using.items():
            f = self.AVAILABLE_FETCHERS[fetcher](
                value,
                self.uri,
                username=self.username,
                password=self.password,
                realm=self.realm,
            )

            for credential in self.required_credentials():
                setattr(self, '_%s' % credential, getattr(f, credential))

        return (self.username, self.password, self.realm, self.uri)
