
from unittest2 import TestCase
import mock
import StringIO

from isotoma.buildout.basicauth import download


class TestStripAuth(TestCase):

    def test_no_auth(self):
        stripped = download.strip_auth("http://www.isotoma.com")
        self.assertEquals(stripped, "http://www.isotoma.com")

    def test_auth(self):
        stripped = download.strip_auth("http://andy:penguin55@isotoma.com")
        self.assertEquals(stripped, "http://isotoma.com")


class TestInjectCredentials(TestCase):

    def test_inject_nothing(self):
         url = download._inject_credentials("http://www.isotoma.com/")
         self.assertEquals(url, "http://www.isotoma.com/")

    def test_inject_nothing_already_has_creds(self):
        url = download._inject_credentials("http://andy:penguin55@www.isotoma.com/")
        self.assertEquals(url, "http://andy:penguin55@www.isotoma.com/")

    def test_inject(self):
        url = download._inject_credentials("http://www.isotoma.com/", "andy", "penguin55")
        self.assertEquals(url, "http://andy:penguin55@www.isotoma.com/")

    def test_inject_already_has(self):
        url = download._inject_credentials("http://andy:penguin55@www.isotoma.com/", "john", "password")
        self.assertEquals(url, "http://andy:penguin55@www.isotoma.com/")


class MockPopper(object):
    def __init__(self, *args):
        self.args = list(args)
    def __call__(self, *args, **kwargs):
        res = self.args.pop(0)
        if isinstance(res, Exception):
            raise res
        return res


class AuthException(Exception):
    code = 401


class TestInjectionDecorator(TestCase):

    def setUp(self):
        self.credentials = mock.Mock()
        self.credentials.search.return_value = [(None, None, False)]

        self.auth_func = mock.Mock()
        self.auth_func.return_value = download.addinfourl(StringIO.StringIO("SUCCESS"), {}, '', 200)

        self.func = download.inject_credentials(self.credentials)(self.auth_func)

    def test_passthru(self):
        self.assertEquals(self.func("http://www.isotoma.com/").read(), "SUCCESS")
        self.assertEquals(self.auth_func.call_count, 1)

    def test_passthru_2(self):
        self.auth_func.side_effect=MockPopper(AuthException("boom"), download.addinfourl(StringIO.StringIO("SUCCESS"), {}, '', 200))

        self.credentials.search.return_value.append(("andy", "penguin55", True))
        self.assertEquals(self.func("http://www.isotoma.com/").read(), "SUCCESS")
        self.assertEquals(self.auth_func.call_count, 2)

