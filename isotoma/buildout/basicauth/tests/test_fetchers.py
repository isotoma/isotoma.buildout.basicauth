from unittest2 import TestCase
import mock

from isotoma.buildout.basicauth import fetchers


class TestKeyring(TestCase):

    def setup_keyring(self, username=None, password=None):
        patcher = mock.patch("isotoma.buildout.basicauth.fetchers.keyring")
        self.keyring = patcher.start()
        self.addCleanup(patcher.stop)

        self.backend = mock.Mock()
        self.keyring.core.load_keyring.return_value = self.backend

        if username and password:
            self.keyring.get_password.return_value = "%s:|%s" % (username, password)
        else:
            self.keyring.get_password.return_value = None

        return fetchers.KeyringFetcher(mock.Mock())

    def test_success(self):
        fetcher = self.setup_keyring()
        fetcher.success("http://www.isotoma.com", "andy", "penguin55")
        self.keyring.set_password.assert_called_with("isotoma.buildout.basicauth", "http://www.isotoma.com", "andy:|penguin55")

    def test_search_match(self):
        fetcher = self.setup_keyring("john", "sjis")
        matches = list(fetcher.search("http://githib.com/isotoma", "http://github.com"))
        self.failUnlessEqual(len(matches), 1)
        self.failUnlessEqual(matches[0], ["john", "sjis"])

    def test_search_fail(self):
        fetcher = self.setup_keyring()
        matches = list(fetcher.search("http://github.com/isotoma", "http://github.com"))
        self.failUnlessEqual(len(matches), 0)


class TestPromptFetcher(TestCase):

    def setUp(self):
        self.username = ''
        self.password = ''

        patcher = mock.patch("__builtin__.raw_input")
        self.raw_input = patcher.start()
        self.raw_input.side_effect = lambda msg: self.username
        self.addCleanup(patcher.stop)

        patcher = mock.patch("getpass.getpass")
        self.getpass = patcher.start()
        self.getpass.side_effect = lambda msg: self.password
        self.addCleanup(patcher.stop)

        self.fetcher = fetchers.PromptFetcher(mock.Mock())

    def test_non_interactive(self):
        self.fetcher.mgr.interactive = False
        self.assertEqual(len(list(self.fetcher.search("a", "b"))), 0)
        self.assertEqual(self.raw_input.call_count, 0)
        self.assertEqual(self.getpass.call_count, 0)

    def test_prompt(self):
        self.username = "jhon"
        self.password = "penguin55"
        walker = self.fetcher.search("a", "b")
        self.assertEqual(walker.next(), ("jhon", "penguin55"))

        self.username = "john"
        self.password = "penguin55"
        self.assertEqual(walker.next(), ("john", "penguin55"))

        self.assertEqual(self.raw_input.call_count, 2)
        self.assertEqual(self.getpass.call_count, 2)

    def test_max_retries(self):
        self.assertEqual(len(list(self.fetcher.search("a", "b"))), 5)
        self.fetcher.max_tries = 55
        self.assertEqual(len(list(self.fetcher.search("a", "b"))), 55)


class TestLovely(TestCase):

    def setUp(self):
        self.mgr = mock.Mock()
        self.part = {}
        self.mgr.buildout = {"lovely.buildouthttp": self.part}

        self.fetcher = fetchers.LovelyFetcher(self.mgr)

    def test_empty_buildout(self):
        self.mgr.buildout = {}
        self.assertEqual(len(list(self.fetcher.search("http://www.isotoma.com", ""))), 0)

    def test_empty_part(self):
        self.assertEqual(len(list(self.fetcher.search("http://www.isotoma.com", ""))), 0)

    def test_empty_uri(self):
        self.part.update(dict(username="john", password="password"))
        self.assertEqual(len(list(self.fetcher.search("http://www.isotoma.com", ""))), 0)

    def test_empty_username(self):
        self.part.update(dict(uri="http://www.isotoma.com", password="password"))
        self.assertEqual(len(list(self.fetcher.search("http://www.isotoma.com", ""))), 0)

    def test_empty_password(self):
        self.part.update(dict(uri="http://www.isotoma.com", username="john"))
        self.assertEqual(len(list(self.fetcher.search("http://www.isotoma.com", ""))), 0)

    def test_match(self):
        self.part.update(dict(uri="http://www.isotoma.com", username="john", password="password"))

        matches = list(self.fetcher.search("http://www.isotoma.com", ""))
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0], ("john", "password"))


