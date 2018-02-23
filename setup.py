from setuptools import setup

setup(
    name='coinrankchat-api',
    packages=['coinrankchat.api'],
    include_package_data=True,
    install_requires=[
        'elasticsearch-dsl', 'falcon'
    ]
)
