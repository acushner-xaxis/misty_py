from setuptools import setup

setup(
    name='misty_py',
    version='0.9.11',
    packages=['misty_py', 'misty_py.utils'],
    package_dir={'misty_py': 'misty_py',
                 'misty_py.utils': 'misty_py/utils'},
    url='https://github.com/acushner-xaxis/misty_py',
    license='MIT',
    author='adam cushner',
    author_email='adam.cushner@gmail.com',
    description='async rest API implementation for misty robots',

    install_requires=['aioconsole', 'arrow', 'requests', 'websockets', 'Pillow', 'sty'],
)
