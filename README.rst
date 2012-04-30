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
    prompt = yes

    [github]
    uri = https://raw.github.com/
    username = user
    password = chunky

In your basicauth part you define each of the credentials parts.

Each of the credentials parts provides authentication details for a different
uri. The part must contain a uri, and specify what methods to use to obtain
the other credentials details.

These credential-fetching methods will be tried in order, until all of the
required credentials have been fetched.

The "interactive" option determines whether or not fetcher methods can prompt
the user for input.

