#!/bin/bash
# Startup script for a trial VM: docker + a host venv for the harness. CPU only.
set -euo pipefail
umask 022
mkdir -p /opt/pxrd /var/log/pxrd
exec >> /var/log/pxrd/bootstrap.log 2>&1
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq docker.io python3-venv ca-certificates curl git unzip
systemctl enable --now docker
python3 -m venv /opt/pxrd/venv
/opt/pxrd/venv/bin/pip install -q 'httpx==0.28.1' 'Pillow==11.3.0' pymatgen spglib rdkit gemmi networkx numpy scipy
chmod -R a+rX /opt/pxrd/venv
touch /opt/pxrd/bootstrap.ready
