"""
"""

import logging

from setuptools import package_index

import urllib
from zc.buildout import UserError

import missingbits
from isotoma.buildout.basicauth.credentials import Credentials
from isotoma.buildout.basicauth.protected_ext import load_protected_extensions
from isotoma.buildout.basicauth.download import inject_credentials, inject_urlretrieve_credentials

logger = logging.getLogger('isotoma.buildout.basicauth')

def install(buildout):
    buildout._raw.setdefault('basicauth', {})
    basicauth = buildout['basicauth']
    basicauth.setdefault('interactive', 'yes')
    basicauth.setdefault('fetch-order', '\n'.join(("lovely", "buildout", "pypi", "prompt")))

    credentials = Credentials(
        buildout,
        fetchers = basicauth.get_list("fetch-order"),
        interactive = basicauth.get_bool("interactive"),
        )

    # Monkeypatch distribute
    logger.info('Monkeypatching distribute to add http auth support')
    package_index.open_with_auth = inject_credentials(credentials)(package_index.open_with_auth)

    logger.info('Monkeypatching urllib.urlretrieve to add http auth support')
    urllib.urlretrieve = inject_urlretrieve_credentials(credentials)(urllib.urlretrieve)

    # Load the buildout:protected-extensions now that we have basicauth
    load_protected_extensions(buildout)
