from unittest2 import TestCase
import mock

from zc.buildout import UserError
from isotoma.buildout.basicauth import credentials
from isotoma.buildout.basicauth import fetchers


class FakeFetcherA(fetchers.Fetcher):
    name = "testa"

    def search(self, *args):
        yield "example1", "password", True

class FakeFetcherB(fetchers.Fetcher):
    name = "testb"

    def search(self, *args):
        if False:
            yield "example2", "password", True


class TestCredentialsMgr(TestCase):

    def setUp(self):
        self.buildout = mock.Mock()
        self.creds = credentials.Credentials(self.buildout, ["testa", "testb"], True)
        patcher = mock.patch.object(FakeFetcherA, "success")
        self.successa = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch.object(FakeFetcherB, "success")
        self.successb = patcher.start()
        self.addCleanup(patcher.stop)

    def test_add_fetcher(self):
        self.assertRaises(UserError, self.creds.add_fetcher, "wibble wibble im not a fetcher")

    def test_get_realm(self):
        self.assertEqual(self.creds.get_realm("http://www.isotoma.com/foo/bar/baz"), "http://www.isotoma.com/")

    def test_success(self):
        self.creds.success("http://pypi.python.org/simple/AccessControl/wibble.tar.gz", "john", "penguin55", True)
        self.assertEqual(self.creds.urls["http://pypi.python.org/"], ("john", "penguin55"))

        self.successa.assert_called_with("http://pypi.python.org/", "john", "penguin55")
        self.assertEqual(self.successa.call_count, 1)

        self.successb.assert_called_with("http://pypi.python.org/", "john", "penguin55")
        self.assertEqual(self.successb.call_count, 1)

    def test_search(self):
        creds = list(self.creds.search("http://www.isotoma.com/"))
        self.assertEqual(creds, [(None, None, False), ("example1", "password", True)])

    def test_search_after_success(self):
        self.creds.urls['http://www.isotoma.com/'] = ("john", "penguin55")
        creds = list(self.creds.search("http://www.isotoma.com/"))
        self.assertEqual(creds, [("john", "penguin55", False), ("example1", "password", True)])

