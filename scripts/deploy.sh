#!/bin/bash
set -e

cargo build --release

ssh pi "sudo /bin/systemctl stop randal"

scp target/armv7-unknown-linux-musleabihf/release/randal pi:/srv

ssh pi "sudo /bin/systemctl start randal"
