#!/bin/bash
set -e

cargo build --release

ansible-playbook -i ansible/inventory.ini ansible/randal.yaml
