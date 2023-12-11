#!/bin/bash
set -e

scp ./randal.service pi:/tmp

ssh -t pi "sudo mv /tmp/randal.service /etc/systemd/system/multi-user.target.wants/randal.service"

ssh -t pi "sudo systemctl enable randal"
