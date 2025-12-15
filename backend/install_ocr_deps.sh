#!/bin/bash

# Carrega NVM
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# Verifica node/npm
node -v
npm -v

# Vai para o diretório do frontend
cd frontend_v2

# Instala a dependência
echo "Installing use-image..."
npm install use-image

echo "Done!"
