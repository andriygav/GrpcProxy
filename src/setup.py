import io
from setuptools import setup, find_packages

from grpc_proxy import __version__

def read(file_path):
    with io.open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


readme = read('README.rst')
requirements = read('requirements.txt')


setup(
    # metadata
    name='grpc_proxy',
    version=__version__,
    license='MIT',
    author='Andrey Grabovoy',
    author_email="grabovoy.av@phystech.edu",
    description='simple grpc proxy.',
    long_description=readme,
    url='https://github.com/andriygav/GrpcProxy',

    # options
    packages=find_packages(),
    install_requires=requirements,
)