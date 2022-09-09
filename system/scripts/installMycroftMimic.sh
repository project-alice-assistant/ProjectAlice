#!/usr/bin/env bash

#
# Copyright (c) 2021
#
# This file, installMycroftMimic.sh, is part of Project Alice.
#
# Project Alice is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>
#
# Last modified: 2021.04.13 at 12:56:49 CEST
#

cd ~ || exit

if [[ -d "mimic" ]]; then
  rm -rf mimic
fi

git clone https://github.com/MycroftAI/mimic1.git
cd mimic1 || exit
./dependencies.sh --prefix="/usr/local"
./autogen.sh
./configure --prefix="/usr/local"
make
/sbin/ldconfig
make check
mv ~/mimic1 ~/mimic
sleep 1
