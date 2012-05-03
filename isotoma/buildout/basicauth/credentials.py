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
        return urlunparse((pr[0], pr[0], '/', '', '', ''))

    def search(self, url):
        realm = self.get_realm(url)
        if realm in self.urls:
            logger.debug("Using previously successful credentials")
            yield self.urls[realm]
        else:
            logger.debug("First time seeing this URL - trying with no credentials")
            yield None, None

        for f in self.fetchers:
            logger.debug("Searching '%s' for credentials" % f.name)
            for cred in f.search(url, realm):
                yield cred

    def success(self, url, username, password):
        self.urls[self.get_realm(url)] = (username, password)

