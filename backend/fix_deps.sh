#!/bin/bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

cd "$(dirname "$0")/frontend_v2"

set -e

echo "Installing tailwind deps..."
npm install -D tailwindcss postcss autoprefixer

echo "Installing konva deps..."
npm install react-konva konva lucide-react clsx tailwind-merge

echo "Init tailwind..."
npx tailwindcss init -p

echo "Done."
