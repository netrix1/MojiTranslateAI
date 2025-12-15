#!/usr/bin/env bash
set -euo pipefail

sudo apt update
sudo apt install -y \
  python3 python3-venv python3-pip git build-essential \
  libjpeg-dev zlib1g-dev \
  libglib2.0-0 libsm6 libxext6 libxrender1

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR/backend"

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip wheel setuptools
pip install -r requirements.txt

echo "Base OK."
echo "Agora instale PyTorch (CPU ou ROCm) e depois: pip install -r requirements-ocr-mangaocr.txt"
