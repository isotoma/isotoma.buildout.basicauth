import logging

from isotoma.buildout.basicauth.fetchers import (
    PyPiRCFetcher,
    KeyringFetcher,
    PromptFetcher,
)

logger = logging.getLogger(__name__)

class Credentials(object):
    """
    A class to instantiate then iterate over `Fetcher`s to acquire a full set
    of credentials for a particular URI.
    """

    AVAILABLE_FETCHERS = {
        'use-pypirc': PyPiRCFetcher,
    #    'keyring': KeyringFetcher,
        'prompt': PromptFetcher,
    }

    def __init__(self, uri, interactive=False, fetch_using=[], **kwargs):
        self.uri = uri
        self._username = kwargs.get('username')
        self._password = kwargs.get('password')
        self._fetch_using = fetch_using
        self._interactive = interactive
        self._fetchers = []
        self._successful_creds = None

    def find_or_create(self, fetcher_name, parameter, ignore_missing=False):
        """Instantiate or reuse an existing fetcher object"""
        try:
            fetcher_cls = self.AVAILABLE_FETCHERS[fetcher_name]
        except KeyError, e:
            if ignore_missing:
                logger.debug('No credential fetcher for key "%s".' % e.args[0])
                return None
            else:
                raise

        f_obj = None
        for _f in self._fetchers:
            if isinstance(_f, fetcher_cls):
                f_obj = _f
        if not f_obj:
            f_obj = fetcher_cls(
                parameter,
                self.uri,
                username=self._username,
                password=self._password,
                interactive=self._interactive,
            )
            self._fetchers.append(f_obj)
        return f_obj

    def get_credentials(self, ignore_missing=True):
        """Iterate across all of the fetchers yielding their credentials (if
        they have any)"""
        if self._successful_creds:
            yield self._successful_creds

        # Allow for hard-coded credentials
        if self._username and self._password:
            yield (self._username, self._password, self.uri)

        fetch_iters = []
        for fetcher_name, parameter in self._fetch_using.items():
            f = self.find_or_create(fetcher_name, parameter, ignore_missing)
            if f:
                fetch_iters.append(f.credentials())

        next_iters = fetch_iters

        while len(next_iters):
            fetch_iters = list(next_iters)
            next_iters = []
            for fetch_iter in fetch_iters:
                try:
                    self._current_creds = fetch_iter.next()
                    next_iters.append(fetch_iter)
                    yield self._current_creds
                except StopIteration:
                    continue

    def success(self):
        self._successful_creds = self._current_creds

        if hasattr(self, '_current_creds'):
            for f in self._fetchers:
                a = (self._current_creds.username, self._current_creds.password)
                f.success(*a)
