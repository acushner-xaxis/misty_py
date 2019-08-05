#!/usr/bin/env bash

set -e

if [[ ! -e misty_py/api.py ]] ; then
  # Not running from within the repo
  if [[ ! -e misty_py/requirements.txt ]] ; then
    # We don't have a checkout
    echo "This will check out a new repository into $(pwd)/misty_py"
    echo "Press enter to continue, ^C to abort"
    read
    echo
    git clone https://github.com/acushner-xaxis/misty_py.git
  fi
  cd misty_py
fi

echo "Creating Python environment in $(pwd)/.virtualenv/"
python3.7 -m venv .virtualenv
.virtualenv/bin/pip install --upgrade pip
.virtualenv/bin/pip install -e .
.virtualenv/bin/pip install -r jupyter-requirements.txt

echo
echo "Done!"
echo "Run:"
echo
echo "  MISTY_IP=192.186.my.ip ./run-jupyter"
echo
echo "to start Jupyter Notebooks and interact in your web browser"
