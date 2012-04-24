"""
In order to support most means of downloading things via buildout, we need to
monkeypatch zc.buildout.download with a custom 401 handler, and add a custom
handler to urllib2.opener.handlers.
"""

import logging
import urllib
import urllib2

logger = logging.getLogger(__name__)

from zc.buildout import download

class CredentialManager(urllib2.HTTPPasswordMgr):
    """A credential manager, conforming to the interface of
    urllib2.HTTPPasswordMgr"""

    def __init__(self):
        self.credentials = {}

    def add_password(self, credential):
        self.credentials[self.reduce_uri(credential.uri)[0]] = credential

    def add_passwords(self, credentials):
        for c in credentials:
            self.add_password(c)

    def find_user_password(self, realm, authuri):
        for default_port in True, False:
            reduced_authuri = self.reduce_uri(authuri, default_port)
            c = self.credentials.get(reduced_authuri[0], None)
            if c:
                user, password, realm, uri = c.get_credentials()
                return user, password
            else:
                for c in self.credentials.itervalues():
                    if self.is_suburi(c.uri, reduced_authuri):
                        user, password, realm, uri = c.get_credentials()
                        return (user, password)

        logger.critical('Could not locate a username and password')
        return (None, None)

class RetryingBasicAuthHandler(urllib2.HTTPBasicAuthHandler):
    def http_error_401(self, req, fp, code, msg, headers):
        logger.critical('WUT')
        raise Exception()
        try:
            self.retried = 0
        except AttributeError:
            pass

        try:
            res = urllib2.HTTPBasicAuthHandler.http_error_401(
                self, req, fp, code, msg, headers
            )
        except urllib2.HTTPError, err:
            raise
        except Exception, err:
            raise
        else:
            if res:
                if res.code >= 400:
                    pass
                else:
                    pass
            return res


class URLOpener(download.URLOpener):
    credentials = []

    def prompt_user_passwd(self, host, realm):
        for c in credentials:
            if c.uri == host:
                user, password, r, u = c.get_credentials()
                return user, password

        return None, None

def add_urllib2_handler(cred_manager):
    logging.debug('Adding urllib2 Authentication Handler')
    auth_handler = urllib2.HTTPBasicAuthHandler(password_mgr=cred_manager)
    handlers = []
    if urllib2._opener is not None:
        handlers[:] = urllib2._opener.handlers
    handlers.insert(0, auth_handler)
    opener = urllib2.build_opener(*handlers)
    urllib2.install_opener(opener)

def patch_buildout_download(*credentials):
    logging.debug('Paching zc.buildout.download.url_opener')
    download.url_opener = URLOpener()
    download.url_opener.credentials = credentials
