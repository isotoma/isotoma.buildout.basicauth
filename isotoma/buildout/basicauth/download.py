"""
In order to support most means of downloading things via buildout, we need to
monkeypatch zc.buildout.download with a custom 401 handler, and add a custom
handler to urllib2.opener.handlers.
"""

import logging
import urllib
import urllib2
import urlparse
import base64

logger = logging.getLogger(__name__)

from zc.buildout import download

def credential_for_url(url, credentials):
    """Given a list of `Credential` objects, find the one pertaining to the
    relevant URL"""

    this_netloc = urlparse.urlparse(url)[1]
    for credential in credentials:
        netloc = urlparse.urlparse(credential.uri)[1]
        if netloc == this_netloc:
            return credential

def _inject_credentials(url, username=None, password=None):
    """Used by `inject_credentials` decorators to actually do the injecting"""

    if username and password:
        scheme, netloc, path, params, query, frag = urlparse.urlparse(url)
        if scheme in ('http', 'https'):
            auth, host = urllib2.splituser(netloc)
            if not auth: # If the URL doesn't have credentials in it already
                netloc = '%s:%s@%s' % (
                    urllib.quote(username),
                    urllib.quote(password),
                    host,
                )
                url = urlparse.urlunparse((scheme,netloc,path,params,query,frag))
    return url

def inject_credentials(credentials):
    """Decorator factory returning a decorator that will keep injecting the
    relevant `Credential` into a URL until the `Credential` is exhausted."""

    def decorator(auth_func):
        def wrapper(url):
            logger.info('Fetching URL %s' % url)
            credential = credential_for_url(url, credentials)
            if not credential:
                logger.debug('No credentials for URL %s' % url)
                return auth_func(url)

            for cred_tuple in credential.get_credentials():
                try:
                    new_url = _inject_credentials(url, cred_tuple[0], cred_tuple[1])
                    return auth_func(new_url)
                except Exception, e:
                    code = getattr(e, 'code', 'unknown')
                    if code == 401:
                        logger.critical('Credentials for %s failed.' % url)
                    else:
                        logger.critical('Cannot fetch %s (%r)' % (url, code))

            # If we still haven't managed to return a value, re-raise
            if e: raise e

        return wrapper
    return decorator
