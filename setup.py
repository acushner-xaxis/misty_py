from setuptools import setup

setup(
    name='misty_py',
    version='0.9.17',
    packages=['misty_py', 'misty_py.utils', 'misty_py.apis'],
    package_dir={'misty_py': 'misty_py',
                 'misty_py.utils': 'misty_py/utils',
                 'misty_py.apis': 'misty_py/apis'
                 },
    url='https://github.com/acushner-xaxis/misty_py',
    license='MIT',
    author='adam cushner',
    author_email='adam.cushner@gmail.com',
    description='async rest API implementation for misty robots',

    install_requires=['arrow', 'requests', 'websockets', 'Pillow', 'sty']
)
