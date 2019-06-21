from setuptools import setup

setup(
    name='mqtt_decorator',
    version='',
    packages=['smarthome', 'smarthome.bindings', 'mqtt_decorator'],
    url='',
    license='',
    author='andrewgermanovich',
    author_email='',
    description='',
    tests_require=['pytest', 'pytest-asyncio', 'pytest-mock'],
    install_requires=['pyyaml', 'attrs', 'hbmqtt', 'astral'
        , 'wrapt'
        , 'git+https://github.com/andvikt/megad2.git'
        , 'git+https://github.com/andvikt/asyncio_primitives.git'
        ]
)
