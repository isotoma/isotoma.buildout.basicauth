import logging

from isotoma.buildout.basicauth.fetchers import (
    PyPiRCFetcher,
    KeyringFetcher,
)

logger = logging.getLogger(__name__)

class Credentials(object):
    """
    A class to instantiate then iterate over `Fetcher`s to acquire a full set
    of credentials for a particular URI.
    """

    AVAILABLE_FETCHERS = {
        'use-pypirc': PyPiRCFetcher,
        'keyring': KeyringFetcher,
    }

    def __init__(self, uri, interactive=False, fetch_using=[], **kwargs):
        self.uri = uri
        self._username = kwargs.get('username')
        self._password = kwargs.get('password')
        self._realm = kwargs.get('realm')
        self._fetch_using = fetch_using
        self._interactive = interactive

    def required_credentials(self):
        required = []

        if not self._username:
            required.append('username')

        if not self._password:
            required.append('password')

        if not self._realm:
            required.append('realm')

        return required

    def get_credentials(self, ignore_missing=True):
        """Iterate across all of the available fetchers until we acquire all of
        the credentials we require"""

        self.exhausted_fetchers = []

        for fetcher, value in self._fetch_using.items():
            try:
                f = self.AVAILABLE_FETCHERS[fetcher](
                    value,
                    self.uri,
                    username=self._username,
                    password=self._password,
                    realm=self._realm,
                    interactive=self._interactive,
                )

                for credential in self.required_credentials():
                    setattr(self, '_%s' % credential, getattr(f, credential))

                self.exhausted_fetchers.append(f)
            except KeyError, e:
                if ignore_missing:
                    logger.warning('No credential fetcher for key "%s".' % e.args[0])
                else:
                    raise

        yield (self._username, self._password, self._realm, self.uri)

    def success(self):
        for f in self.exhausted_fetchers:
            f.success(self._username, self._password, self._realm)
