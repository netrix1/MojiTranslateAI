#!/usr/bin/env bash
set -euo pipefail

# Reaplica o workaround que funcionou em WSL2 (Ubuntu 22.04.5):
# - usa libhsa-runtime64 do /opt/rocm dentro do torch
#
# Uso:
#   ./backend/scripts/repair_torch_rocm_wsl.sh [CAMINHO_DA_VENV]
#
# Exemplo:
#   ./backend/scripts/repair_torch_rocm_wsl.sh backend/.venv

VENV_DIR="${1:-.venv}"

source "$VENV_DIR/bin/activate"

TORCH_LIB=$(python - <<'PY'
import os, torch
print(os.path.join(os.path.dirname(torch.__file__), "lib"))
PY
)

HSA=$(ls -1 /opt/rocm/lib/libhsa-runtime64.so.* 2>/dev/null | sort -V | tail -n 1)

echo "TORCH_LIB=$TORCH_LIB"
echo "HSA=$HSA"

cd "$TORCH_LIB"
rm -f libhsa-runtime64.so*
cp "$HSA" libhsa-runtime64.so

python - <<'PY'
import torch
print("is_available:", torch.cuda.is_available())
print("device_count:", torch.cuda.device_count())
if torch.cuda.is_available():
    print("device[0]:", torch.cuda.get_device_name(0))
PY
