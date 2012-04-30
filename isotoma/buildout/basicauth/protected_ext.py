import os
import pkg_resources
from zc.buildout import easy_install

def load_protected_extensions(buildout=None):
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
