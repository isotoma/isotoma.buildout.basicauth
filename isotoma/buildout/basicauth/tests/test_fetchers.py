from unittest2 import TestCase
import mock
import StringIO

from zc.buildout import UserError
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
        self.failUnlessEqual(matches[0], ("john", "sjis", True))

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
        self.assertEqual(walker.next(), ("jhon", "penguin55", True))

        self.username = "john"
        self.password = "penguin55"
        self.assertEqual(walker.next(), ("john", "penguin55", True))

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
        self.assertEqual(matches[0], ("john", "password", True))


def FakeOption(**kwargs):
    actual = {}
    actual.update(kwargs)

    def get(k):
        try:
            return actual[k]
        except KeyError:
            raise UserError("Missing key '%s'" % k)

    def get_list(k):
        value = get(k).strip()
        if not value:
            return []
        return [x.strip() for x in value.split("\n") if x.strip()]

    mocked = mock.MagicMock()
    mocked.__getitem__.side_effect = get
    mocked.__setitem__.side_effect = actual.__setitem__
    mocked.__delitem__.side_effect = actual.__delitem__
    mocked.__contains__.side_effect = actual.__contains__
    mocked.get_list.side_effect = get_list
    return mocked


class TestBuildout(TestCase):

    def setUp(self):
        self.mgr = mock.Mock()

        self.basicauth = FakeOption(credentials="isotoma")
        self.isotoma = FakeOption(
            uri = "http://www.isotoma.com",
            username = "john",
            password = "password",
            )
        self.mgr.buildout = FakeOption(basicauth=self.basicauth, isotoma=self.isotoma)

    def test_empty_buildout(self):
        self.mgr.buildout = {}
        self.fetcher = fetchers.BuildoutFetcher(self.mgr)
        self.assertEqual(len(list(self.fetcher.search("http://www.isotoma.com", ""))), 0)

    def test_empty_part(self):
        self.mgr.buildout["basicauth"] = {}
        self.fetcher = fetchers.BuildoutFetcher(self.mgr)
        self.assertEqual(len(list(self.fetcher.search("http://www.isotoma.com", ""))), 0)

    def test_empty_creds_list(self):
        self.basicauth["credentials"] = ""
        self.fetcher = fetchers.BuildoutFetcher(self.mgr)
        self.assertEqual(len(list(self.fetcher.search("http://www.isotoma.com", ""))), 0)

    def test_empty_missing_part(self):
        del self.mgr.buildout["isotoma"]
        self.assertRaises(UserError, fetchers.BuildoutFetcher, self.mgr)

    def test_empty_uri(self):
        del self.isotoma["uri"]
        self.assertRaises(UserError, fetchers.BuildoutFetcher, self.mgr)

    def test_empty_username(self):
        del self.isotoma["username"]
        self.assertRaises(UserError, fetchers.BuildoutFetcher, self.mgr)

    def test_empty_password(self):
        del self.isotoma["password"]
        self.assertRaises(UserError, fetchers.BuildoutFetcher, self.mgr)

    def test_match(self):
        self.fetcher = fetchers.BuildoutFetcher(self.mgr)
        matches = list(self.fetcher.search("http://www.isotoma.com", ""))
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0], ("john", "password", True))


class TestPyPiRCFetcher(TestCase):

    def setUp(self):
        patcher = mock.patch("os.path.exists")
        self.exists = patcher.start()
        self.addCleanup(patcher.stop)
        self.exists.return_value = False

        patcher = mock.patch("ConfigParser.open", create=True)
        self.open = patcher.start()
        self.addCleanup(patcher.stop)

    def search(self, uri="http://foo.local/"):
        f = fetchers.PyPiRCFetcher(mock.Mock())
        return list(f.search(uri, uri))

    def test_no_rc(self):
        self.assertEqual(len(self.search()), 0)

    def test_empty_rc(self):
        self.exists.return_value = True
        self.open.side_effect = lambda x: StringIO.StringIO("\n")
        self.assertEqual(len(self.search()), 0)

    def test_valid_rc(self):
        self.exists.return_value = True
        self.open.side_effect = lambda x: StringIO.StringIO(
            "[distutils]\n"
            "index-servers =\n"
            "    apple\n"
            "    orange\n"
            "    banana\n"
            "[orange]\n"
            "repository:http://orange.local/\n"
            "username = orange\n"
            "password = password\n"
            "[apple]\n"
            "repository = http://apple.local/\n"
            "username = apple\n"
            "password = password\n"
            "[banana]\n"
            "repository = http://banana.local/\n"
            "[server-login]\n"
            "repository = http://server.local/\n"
            "username = server\n"
            "password = password\n"
            )

        self.assertEqual(len(self.search()), 0)
        self.assertEqual(len(self.search("http://banana.local/simple")), 0)

        matches = self.search("http://apple.local/simple/a/")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0], ("apple", "password", True))

        matches = self.search("http://server.local/simple/a/")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0], ("server", "password", True))



