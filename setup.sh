#!/bin/bash

set -e
set -x

# python dependencies
sudo pip3 install -r requirements.txt

# tooling dependences
git submodule update --init --recursive
pushd tools/intel-cmt-cat
make -j$(nproc) -C lib
make -j$(nproc) -C pqos
popd
