#!/bin/bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

cd "$(dirname "$0")/frontend_v2"

echo "Installing base dependencies..."
npm install

echo "Installing additional dependencies..."
npm install -D tailwindcss postcss autoprefixer
npm install react-konva konva lucide-react clsx tailwind-merge

echo "Initializing Tailwind..."
npx tailwindcss init -p
