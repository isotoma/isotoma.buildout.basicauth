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
    realm = github

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

import missingbits

from isotoma.buildout.basicauth.credentials import Credentials
from isotoma.buildout.basicauth.protected_ext import load_protected_extensions
from isotoma.buildout.basicauth.download import (
    CredentialManager,
    add_urllib2_handler,
    patch_buildout_download,
)

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
        exclude = ('uri', 'username', 'password', 'realm')
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
            realm=stanza.get('realm'),
            fetch_using=fetch_methods,
            interactive=interactive,
        ))

    return credentials

def install(buildout):
    """Install the basicauth extension"""

    # urllib2
    credentials = _retrieve_credentials(buildout)
    manager = CredentialManager()
    manager.add_passwords(credentials)
    add_urllib2_handler(manager)

    # zc.buildout.download
    patch_buildout_download(*credentials)

    # Now load any protected-extensions using over basicauth
    load_protected_extensions(buildout)
