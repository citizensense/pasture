#!/bin/sh 
## Finding Song Home embedded system for Kaffe Matthews
## Copyright (C) 2015 Tom Keene
## 
## This program is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
## 
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
## GNU General Public License for more details.
## 
## You should have received a copy of the GNU General Public License
## along with this program. If not, see <http://www.gnu.org/licenses/>.

# Make sure this script is runs as root so processes started by systemd can be killed
LUID=$(id -u)
if [ $LUID -ne 0 ]; then
    echo "$0 must be run as root"
    exit 1
fi

# This script called via systemd
# We use the ps aux method as it seems more reliable than a simple killall
# The killas are encapsulated in if statements so systemd reporting doesnt
# get clogged up

# Function to find all processes and kill them
KillProcess () {
    N=$(ps aux | grep $1 | grep -v grep)
    if [ ! -z "$N" ]; then
        ps aux | grep $1 | awk '{ print $2}' | xargs kill -9
    fi
}

# Kill all running processes
KillProcess autoupdate
