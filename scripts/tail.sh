#!/bin/bash
set -e

ssh pi "sudo journalctl --unit=randal --follow -q"
