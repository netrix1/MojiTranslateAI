# MojiTranslateAI — Tutorial de instalação (Ubuntu 22.04.5 no WSL2) — versão validada até agora

Este guia documenta **exatamente** o que funcionou no seu ambiente até o momento para:
- Rodar o backend FastAPI do **MojiTranslateAI** no **Ubuntu 22.04.5 via WSL2**
- Habilitar **PyTorch + ROCm (GPU AMD)** no WSL
- Instalar e validar **MangaOCR** usando GPU
- Subir a API e acessar o Swagger

> Recomendações:
> - Rode o projeto no filesystem Linux (ex.: `~/projects/...`) e **não** em `/mnt/c/...` para melhor performance de I/O.
> - Este tutorial assume que você já tem WSL2 + Ubuntu 22.04.5 instalado e funcional.

---

## 1) Dependências de sistema (Ubuntu)

```bash
sudo apt update
sudo apt install -y \
  python3 python3-venv python3-pip git build-essential unzip \
  libjpeg-dev zlib1g-dev \
  libglib2.0-0 libsm6 libxext6 libxrender1
```

---

## 2) Colocar o projeto no Linux e entrar no backend

Exemplo (ajuste caminhos conforme seu caso):

```bash
mkdir -p ~/projects
cd ~/projects
# extraia seu zip aqui (ou clone via git)
cd MojiTranslateAI/backend
```

---

## 3) Criar e ativar a venv

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip wheel setuptools
```

---

## 4) Instalar dependências Python do backend

Dentro da venv:

```bash
pip install -r requirements.txt
```

---

## 5) Verificar que o WSL expõe a GPU (pré-check)

```bash
ls -l /dev/dxg
uname -r
rocminfo | head -n 50
rocminfo | grep -E "gfx|Name|Agent" -n | head
```

**Esperado:**
- `/dev/dxg` existe
- `rocminfo` lista um “Agent” da sua GPU, por exemplo `gfx1201` e o nome da placa.

---

## 6) Instalar PyTorch ROCm (ROCm 6.4) e validar

Dentro da venv:

```bash
pip uninstall -y torch torchvision torchaudio pytorch-triton-rocm triton || true
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.4
```

Teste:

```bash
python - <<'PY'
import torch
print("torch:", torch.__version__)
print("hip  :", torch.version.hip)
print("is_available:", torch.cuda.is_available())
print("device_count:", torch.cuda.device_count())
if torch.cuda.is_available():
    print("device[0]:", torch.cuda.get_device_name(0))
PY
```

> Observação: em ROCm no Linux/WSL, o PyTorch usa a API `torch.cuda.*` como interface; isso é normal.

---

## 7) Correção que destravou GPU no WSL (workaround `libhsa`)

No seu caso, mesmo com `rocminfo` OK, o PyTorch inicialmente retornou:
- `is_available: False`
- `device_count: 0`

A correção aplicada que funcionou foi:

### 7.1) Garantir libs do WSL no loader

```bash
echo 'export LD_LIBRARY_PATH=/usr/lib/wsl/lib:${LD_LIBRARY_PATH}' >> ~/.bashrc
source ~/.bashrc
```

### 7.2) Substituir `libhsa-runtime64` dentro do Torch pela versão do `/opt/rocm`

> Execute com a venv ativa:

```bash
source .venv/bin/activate

TORCH_LIB=$(python - <<'PY'
import os, torch
print(os.path.join(os.path.dirname(torch.__file__), "lib"))
PY
)

HSA=$(ls -1 /opt/rocm/lib/libhsa-runtime64.so.* 2>/dev/null | sort -V | tail -n 1)

echo "TORCH_LIB=$TORCH_LIB"
echo "HSA=$HSA"

cd "$TORCH_LIB" || exit 1
rm -f libhsa-runtime64.so*
cp "$HSA" libhsa-runtime64.so
```

### 7.3) Re-testar PyTorch

```bash
python - <<'PY'
import torch
print("torch:", torch.__version__)
print("hip  :", torch.version.hip)
print("is_available:", torch.cuda.is_available())
print("device_count:", torch.cuda.device_count())
if torch.cuda.is_available():
    print("device[0]:", torch.cuda.get_device_name(0))
PY
```

**Esperado (no seu caso):**
- `is_available: True`
- `device_count: 1`
- `device[0]` mostra sua GPU (ex.: `AMD Radeon RX 9070 XT`)

---

## 8) Instalar e validar MangaOCR (com GPU)

Dentro da venv:

```bash
pip install -r requirements-ocr-mangaocr.txt
```

Teste:

```bash
python - <<'PY'
from manga_ocr import MangaOcr
m = MangaOcr()
print("MangaOCR OK")
PY
```

**Esperado (log informativo):**
- “Loading OCR model …”
- “Using CUDA” (normal mesmo em ROCm)
- “OCR ready”
- “MangaOCR OK”

---

## 9) Subir a API FastAPI

Dentro da venv e na pasta `backend/`:

```bash
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Acesse do Windows:

- http://localhost:8000/docs

---

## 10) Observação importante (manutenção do workaround)

Como a correção do `libhsa-runtime64` altera arquivos dentro do `site-packages/torch`, uma reinstalação/upgrade do torch pode desfazer isso.

Recomendação: manter um script de “repair” (ex.: `backend/scripts/repair_torch_rocm_wsl.sh`) para reaplicar rapidamente quando necessário.

---

## 11) Próximos passos do MojiTranslateAI (planejamento)

- Substituir `ocr_stub` por `ocr_mangaocr` no pipeline (OCR real de japonês).
- Posteriormente instalar e integrar **PaddleOCR** como OCR para outras línguas (PT/EN) e/ou como detector de bboxes.
