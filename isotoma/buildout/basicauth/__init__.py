"""
==========================
isotoma.buildout.basicauth
==========================

We expect a config as follows::

    [basicauth]
    credentials =
        pypi
        github
    interactive = yes

    [pypi]
    uri = https://example.com/
    use-pypirc = pypi

    [github]
    uri = https://raw.github.com/

In your basicauth part you define each of the credentials parts.

Each of the credentials parts provides authentication details for a different
uri. The part must contain a uri, and specify what methods to use to obtain
the other credentials details.

These credential-fetching methods will be tried in order, until all of the
required credentials have been fetched.

The "interactive" option determines whether or not fetcher methods can prompt
the user for input.
"""

import os
import sys

from setuptools import package_index

import missingbits
from isotoma.buildout.basicauth.credentials import Credentials
from isotoma.buildout.basicauth.protected_ext import load_protected_extensions
from isotoma.buildout.basicauth.download import inject_credentials

def _retrieve_credentials(buildout):
    basicauth = buildout.get('basicauth')

    basicauth.setdefault('interactive', 'yes')
    interactive = basicauth.get_bool('interactive')

    if basicauth:
        credentials_parts = basicauth.get_list('credentials')
    else: # Legacy mode
        credentials_parts = []

    credentials = []

    for c in credentials_parts:
        exclude = ('uri', 'username', 'password')
        stanza = buildout.get(c)
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
            interactive=interactive,
        ))

    return credentials

def install(buildout):
    """Install the basicauth extension"""

    credentials = _retrieve_credentials(buildout)

    # Monkeypatch distutils
    package_index.open_with_auth = inject_credentials(credentials)(package_index.open_with_auth)
