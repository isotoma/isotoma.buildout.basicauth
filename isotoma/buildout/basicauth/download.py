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

def strip_auth(url):
    scheme, netloc, path, params, query, frag = urlparse.urlparse(url)
    if scheme in ('http', 'https'):
        auth, host = urllib2.splituser(netloc)
        return urlparse.urlunparse((scheme,host,path,params,query,frag))
    return url

def credential_for_url(url, credentials):
    """Given a list of `Credential` objects, find the one pertaining to the
    relevant URL"""
    this_netloc = urlparse.urlparse(url)[1]
    for credential in credentials:
        netloc = urlparse.urlparse(credential.uri)[1]
        if netloc == this_netloc:
            return credential

def call_auth_function(auth_function, url, credentials, *args):
    logger.debug('Downloading URL %s' % strip_auth(url))
    credential = credential_for_url(url, credentials)

    def log_exception(exc, url_e):
        if isinstance(exc, IOError):
            code = exc.args[1]
        else:
            code = getattr(exc, 'code', 'unknown')

        if code in (401, 403):
            logger.critical('Could not authenticate %s. (%d)' % (url_e, code))
        else:
            logger.critical('Cannot fetch %s (%r)' % (url_e, code))
            logger.debug(e)

    if not credential:
        stripped_auth = strip_auth(url)
        if url == stripped_auth:
            logger.debug('No credentials for %s' % stripped_auth)
        try:
            return auth_function(url, *args)
        except Exception, e:
            log_exception(e, stripped_auth)
            raise

    e = None
    for cred_tuple in credential.get_credentials():
        e = None
        try:
            new_url = _inject_credentials(
                url, cred_tuple[0], cred_tuple[1]
            )

            res = auth_function(new_url)
        except Exception, e:
            log_exception(e, url)
        else:
            logger.debug("Credential was successful")
            credential.success()
            return res

    # If we still haven't managed to return a value, re-raise
    if e:
        raise e
    else:
        try:
            return auth_function(url)
        except Exception, e:
            log_exception(e, url)
            raise

def credentials_for_retrieve(credentials):
    def urlretrieve(url, filename=None, reporthook=None, data=None):
        return call_auth_function(url, credentials, filename, reporthook, data)
    return urlretrieve

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
            return call_auth_function(auth_func, url, credentials)
        return wrapper
    return decorator
