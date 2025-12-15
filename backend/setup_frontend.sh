#!/bin/bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm

echo "Node version:"
node -v || echo "Node not found"
echo "NPM version:"
npm -v || echo "NPM not found"

cd "$(dirname "$0")"

if [ -d "frontend_v2" ]; then
    echo "frontend_v2 already exists, skipping creation"
else
    echo "Creating frontend_v2..."
    npm create vite@latest frontend_v2 -- --template react-ts -y
fi
