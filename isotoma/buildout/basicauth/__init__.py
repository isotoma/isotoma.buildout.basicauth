"""
"""

import os
import sys
import logging

from setuptools import package_index

from zc.buildout import UserError

import missingbits
from isotoma.buildout.basicauth.credentials import Credentials
from isotoma.buildout.basicauth.protected_ext import load_protected_extensions
from isotoma.buildout.basicauth.download import inject_credentials

logger = logging.getLogger('isotoma.buildout.basicauth')

def _retrieve_credentials(buildout):
    basicauth = buildout.get('basicauth')

    # Interactive mode by default
    basicauth.setdefault('interactive', 'yes')
    interactive = basicauth.get_bool('interactive')

    basicauth.setdefault('fetch-order', '''\
        use-pypirc
        prompt
    ''')
    fetch_order = basicauth.get_list('fetch-order')

    if basicauth:
        credentials_parts = basicauth.get_list('credentials')
    else: # Legacy mode
        credentials_parts = []

    credentials = []

    for c in credentials_parts:
        exclude = ('uri', 'username', 'password')
        stanza = buildout.get(c)
        if not stanza:
            raise UserError('basicauth part refers to nonexistent "%s" part' % c)
        uri = stanza.get('uri')

        fetch_methods = {}
        for key, value in stanza.iteritems():
            if not key in exclude:
                fetch_methods[key] = value

        credentials.append(Credentials(
            uri=uri,
            username=stanza.get('username'),
            password=stanza.get('password'),
            fetch_using=fetch_methods,
            fetch_order=fetch_order,
            interactive=interactive,
        ))

    return credentials

def install(buildout):
    """Install the basicauth extension"""

    credentials = _retrieve_credentials(buildout)

    logger.info('Monkeypatching distribute to add http auth support')
    # Monkeypatch distribute
    package_index.open_with_auth = inject_credentials(credentials)(package_index.open_with_auth)

    # Load the buildout:protected-extensions now that we have basicauth
    load_protected_extensions(buildout)
