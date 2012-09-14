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
import time
from zc.buildout import UserError
import StringIO

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
                    urllib.quote(username, ''),
                    urllib.quote(password, ''),
                    host_part,
                )
                url = urlparse.urlunparse((scheme,netloc,path,params,query,frag))
    return url


class AuthError(Exception):
    pass

class NotFoundError(Exception):
    pass

class AuthAdaptor(object):

    ATTEMPTS = 3

    def __init__(self, credentials):
        self.credentials = credentials

    def call(self, *args, **kwargs):
        raise NotImplementedError(self.call)

    def attempt(self, *args, **kwargs):
        for i in range(self.ATTEMPTS):
            try:
                return self.call(*args, **kwargs)
            except AuthError:
                raise
            except NotFoundError:
                raise
            except Exception, e:
                logger.exception("Attempt to access resource failed. Will try again in %d seconds" % i)
                time.sleep(i)

        self.broken()

    def broken(self):
        raise UserError("Despite multiple attempts buildout was unable to access a remote resource")

    def forbidden(self):
        raise UserError("Forbidden")

    def not_found(self):
        raise UserError("Resource not found")

    def __call__(self, url, *args, **kwargs):
        logger.debug('Downloading URL %s' % strip_auth(url))

        for username, password, cache in self.credentials.search(url):
            new_url = _inject_credentials(url, username, password)
            try:
                res = self.attempt(new_url, *args, **kwargs)

            except AuthError, e:
                logger.debug('Could not authenticate %s.' % (url, ))

            except NotFoundError, e:
                self.not_found()

            else:
                self.credentials.success(url, username, password, cache)
                return res

        self.forbidden()


class addinfourl(urllib2.addinfourl):

    """ Support Python 2.4 and 2.6 """

    def __init__(self, fp, headers, url, code=None):
        try:
            urllib2.addinfourl.__init__(self, fp, headers, url, code)
        except TypeError:
            urllib2.addinfourl.__init__(self, fp, headers, url)
            self.code = code


def inject_credentials(credentials):
    def decorator(auth_func):
        class DistributeAdaptor(AuthAdaptor):
            def not_found(self):
                raise urllib2.HTTPError('', 404, "Not found", {}, StringIO.StringIO(""))

            def call(self, *args, **kwargs):
                try:
                    r = auth_func(*args, **kwargs)
                    fp = StringIO.StringIO(r.read())
                    resp = addinfourl(fp, r.headers, r.url, r.code)
                    return resp

                except Exception, e:
                    code = getattr(e, 'code', 'unknown')
                    if code in (401, 403):
                        raise AuthError
                    elif code == 404:
                        raise NotFoundError
                    else:
                        raise

        return DistributeAdaptor(credentials)
    return decorator


def inject_urlretrieve_credentials(credentials):
    def decorator(auth_func):
        class UrlRetrieveAdaptor(AuthAdaptor):
            def call(self, *args, **kwargs):
                try:
                    res = auth_func(*args, **kwargs)
                    return res
                except IOError, e:
                    code = e.args[1]
                    if code in (401, 403):
                        raise AuthError
                    elif code == 404:
                        raise NotFoundError
                    else: raise

        return UrlRetrieveAdaptor(credentials)
    return decorator


