from setuptools import setup
from pathlib import Path

with open(Path(__file__).parent / 'README.md') as f:
    long = f.read()

setup(
    name='misty_py',
    version='0.9.27',
    packages=['misty_py', 'misty_py.utils', 'misty_py.apis'],
    package_dir={'misty_py': 'misty_py',
                 'misty_py.utils': 'misty_py/utils',
                 'misty_py.apis': 'misty_py/apis'
                 },
    url='https://github.com/acushner-xaxis/misty_py',
    license='MIT',
    author='adam cushner',
    author_email='adam.cushner@gmail.com',
    description='async/await REST API implementation for misty II robots',
    long_description=long,
    long_description_content_type="text/markdown",

    install_requires=['arrow', 'requests', 'websockets', 'Pillow'],
    classifiers=[
        "Programming Language :: Python :: 3"
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',

)
