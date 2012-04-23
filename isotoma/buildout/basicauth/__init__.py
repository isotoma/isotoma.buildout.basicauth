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

def _load_protected_extensions(buildout=None):
    """
    Because all of the extensions are loaded prior to any of them being
    applied, we have added a protected-extensions option::

        [buildout]
        extensions = isotoma.buildout.basicauth
        protected-extensions =
            isotoma.buildout.autodevelop

    Then every protected extension will be loaded once the basicauth extension
    has been applied, meaning they'll be fetched using credentials.
    """
    if not buildout:
         return

    specs = buildout['buildout'].get('protected-extensions', '').split()
    if specs:
        path = [buildout['buildout']['develop-eggs-directory']]
        if buildout['buildout']['offline'] == 'true':
            dest = None
            path.append(buildout['buildout']['eggs-directory'])
        else:
            dest = buildout['buildout']['eggs-directory']
            if not os.path.exists(dest):
                log.info('Creating directory %r.' % dest)
                os.mkdir(dest)

        easy_install.install(
            specs, dest, path=path,
            working_set=pkg_resources.working_set,
            links = buildout['buildout'].get('find-links', '').split(),
            index = buildout['buildout'].get('index'),
            newest=buildout.newest, allow_hosts=buildout._allow_hosts,
        )   

        # Clear cache because extensions might now let us read pages we
        # couldn't read before.
        easy_install.clear_index_cache()
