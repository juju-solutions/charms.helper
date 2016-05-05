from setuptools import setup


SETUP = {
    'name': "charms.tool",
    'version': '0.0.1',
    'author': "Ubuntu Developers",
    'author_email': "juju@lists.ubuntu.com",
    'url': 'https://github.com/juju-solutions/charms.tool',
    'packages': [
        'charms.tool',
    ],
    'install_requires': [
        'pyaml',
    ],
    'license': "Apache License 2.0",
    'long_description': open('README.rst').read(),
    'description': 'Framework for interacting with charm model tools',
}

try:
    from sphinx_pypi_upload import UploadDoc
    SETUP['cmdclass'] = {'upload_sphinx': UploadDoc}
except ImportError:
    pass

if __name__ == '__main__':
    setup(**SETUP)
