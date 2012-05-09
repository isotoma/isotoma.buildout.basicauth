import logging
from urlparse import urlparse, urlunparse
from zc.buildout import UserError
from isotoma.buildout.basicauth.fetchers import Fetcher

logger = logging.getLogger(__name__)

class Credentials(object):

    def __init__(self, buildout, fetchers, interactive=True):
        self.urls = {}
        self.buildout = buildout
        self.interactive = interactive
        self.fetchers = []
        [self.add_fetcher(f) for f in fetchers]

    def add_fetcher(self, fetchername):
        for f in Fetcher.__subclasses__():
            if f.name == fetchername:
                self.fetchers.append(f(self))
                return
        raise UserError("No fetcher '%s'" % fetchername)

    def get_realm(self, url):
        pr = urlparse(url)
        return urlunparse((pr[0], pr[1], '/', '', '', ''))

    def search(self, url):
        realm = self.get_realm(url)
        if realm in self.urls:
            logger.debug("Using previously successful credentials")
            username, password = self.urls[realm]
            # We say this password can't be cached because it already was cached
            # During a plone buildout that would make us write to the keyring
            # 200 times!!
            yield username, password, False
        else:
            logger.debug("First time seeing this URL - trying with no credentials")
            # We say this password can't be cached because we don't want to
            # send None, None to backends
            yield None, None, False

        for f in self.fetchers:
            logger.debug("Searching '%s' for credentials" % f.name)
            for cred in f.search(url, realm):
                yield cred

    def success(self, url, username, password, cache):
        realm = self.get_realm(url)
        self.urls[realm] = (username, password)
        if cache:
            for f in self.fetchers:
                f.success(realm, username, password)

