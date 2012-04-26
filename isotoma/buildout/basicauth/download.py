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

def credentials_for_url(credentials, url):
    this_netloc = urlparse.urlparse(url)[1]
    for credential in credentials:
        netloc = urlparse.urlparse(credential.uri)[1]
        if netloc == this_netloc:
            username, password, realm, url = credential.get_credentials()
            return username, password
    return None, None

def inject_credentials(credentials):
    def decorator(auth_func):
        def wrapper(url):
            logger.critical('Fetching URL %s' % url)

            scheme, netloc, path, params, query, frag = urlparse.urlparse(url)
            if scheme in ('http', 'https'):
                auth, host = urllib2.splituser(netloc)
                if not auth:
                    username, password = credentials_for_url(credentials, url)
                    if username:
                        netloc = '%s%s@%s' % (username, password, host)
                        url = urlparse.urlunparse((scheme,netloc,path,params,query,frag))
            return auth_func(url)

        return wrapper
    return decorator
