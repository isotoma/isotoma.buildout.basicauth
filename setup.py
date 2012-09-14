from setuptools import setup, find_packages

version = '0.0.5'
long_description = open('README.rst').read() + '\n\n' + open('CHANGES').read()

setup(
    name='isotoma.buildout.basicauth',
    version=version,
    author='Alex Holmes',
    author_email='alex@alex-holmes.com',
    maintainer='John Carr',
    maintainer_email='john.carr@isotoma.com',
    zip_safe=False,
    description='Buildout extension providing basic authentication support',
    long_description=long_description,
    license='Apache Public License',
    keywords='buildout basicauth http authentication',
    packages=find_packages(),
    include_package_data=True,
    namespace_packages=['isotoma', 'isotoma.buildout'],
    install_requires=[
        'setuptools',
        'missingbits',
        'zc.buildout',
        'keyring <= 0.6.2',
    ],
    extras_require={
        "test": ['unittest2', 'mock'],
    },
    entry_points='''
    [zc.buildout.extension]
    default = isotoma.buildout.basicauth:install
    ''',
)
