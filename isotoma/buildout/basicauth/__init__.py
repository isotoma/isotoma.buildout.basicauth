"""
==========================
isotoma.buildout.basicauth
==========================

We expect a config as follows::

    [basicauth]
    credentials =
        pypi
        github

    [pypi]
    uri = https://example.com/
    use-pypirc = pypi

    [github]
    uri = https://raw.github.com/
    realm = github
    prompt = yes

In your basicauth part you define each of the credentials parts.

Each of the credentials parts provides authentication details for a different
uri. The part must contain a uri, and specify what methods to use to obtain
the other credentials details.

These credential-fetching methods will be tried in order, until all of the
required credentials have been fetched.
"""

import os
import sys

from isotoma.buildout.basicauth.credentials import Credentials
from isotoma.buildout.basicauth.protected_ext import _load_protected_extensions
import missingbits

def _retrieve_credentials(buildout):
    basicauth = buildout.get('basicauth')

    if basicauth:
        credentials_parts = basicauth.get_list('credentials')
    else: # Legacy mode
        credentials_parts = []

    credentials = {}

    for c in credentials_parts:
        exclude = ('uri', 'username', 'password', 'realm')
        stanza = buildout.get(c)
        uri = stanza.get('uri')

        fetch_methods = {}
        for key, value in stanza.iteritems():
            if not key in exclude:
                fetch_methods[key] = value

        credentials[c] = Credentials(
            uri=uri,
            username=stanza.get('username'),
            password=stanza.get('password'),
            realm=stanza.get('realm'),
            fetch_using=fetch_methods,
        ).get_credentials()

    return credentials

def install(buildout=None):
    credentials = _retrieve_credentials(buildout)
    print >>sys.stderr,  credentials


