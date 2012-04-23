import logging

from isotoma.buildout.basicauth.fetchers import PyPiRCFetcher

logger = logging.getLogger(__name__)

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
            try:
                f = self.AVAILABLE_FETCHERS[fetcher](
                    value,
                    self._uri,
                    username=self._username,
                    password=self._password,
                    realm=self._realm,
                )
            except KeyError, e:
                if ignore_missing:
                    logger.warning('No credential fetcher for key "%s".' % e.args[0])
                else:
                    raise

            for credential in self.required_credentials():
                setattr(self, '_%s' % credential, getattr(f, credential))

        return (self._username, self._password, self._realm, self._uri)
