#!/bin/bash
set -e

cargo build --release

ssh -t pi "sudo /bin/systemctl stop randal"

scp target/armv7-unknown-linux-musleabihf/release/randal pi:/srv

ssh -t pi "sudo /bin/systemctl start randal"
