from setuptools import setup

setup(
    name='misty_py',
    version='0.9.0',
    packages=['misty_py'],
    url='https://github.com/acushner-xaxis/misty_py',
    license='MIT',
    author='adam cushner',
    author_email='adam.cushner@gmail.com',
    description='async rest API implementation for misty robots',

    install_requires=['arrow', 'requests', 'websockets', 'Pillow', 'sty'],
)
