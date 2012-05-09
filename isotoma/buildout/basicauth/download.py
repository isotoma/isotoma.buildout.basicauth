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

def strip_auth(url):
    scheme, netloc, path, params, query, frag = urlparse.urlparse(url)
    if scheme in ('http', 'https'):
        auth, host = urllib2.splituser(netloc)
        return urlparse.urlunparse((scheme,host,path,params,query,frag))
    return url

def _inject_credentials(url, username=None, password=None):
    """Used by `inject_credentials` decorators to actually do the injecting"""

    if username and password:
        scheme, netloc, path, params, query, frag = urlparse.urlparse(url)
        if scheme in ('http', 'https'):
            auth_part, host_part = urllib2.splituser(netloc)
            if not auth_part: # If the URL doesn't have credentials in it already
                netloc = '%s:%s@%s' % (
                    urllib.quote(username),
                    urllib.quote(password),
                    host_part,
                )
                url = urlparse.urlunparse((scheme,netloc,path,params,query,frag))
    return url

def inject_credentials(credentials):
    """Decorator factory returning a decorator that will keep injecting the
    relevant `Credential` into a URL until the `Credential` is exhausted."""

    def decorator(auth_func):
        def wrapper(url):
            logger.debug('Downloading URL %s' % strip_auth(url))

            e = None

            for username, password, cache in credentials.search(url):
                new_url = _inject_credentials(url, username, password)
                try:
                    res = auth_func(new_url)
                except Exception, e:
                    code = getattr(e, 'code', 'unknown')
                    if code in (401, 403):
                        logger.critical('Could not authenticate %s. (%d)' % (url, code))
                    else:
                        logger.critical('Cannot fetch %s (%r)' % (url, code))
                        logger.debug(e)
                        raise
                else:
                    credentials.success(url, username, password, cache)
                    return res

            raise e

        return wrapper
    return decorator
