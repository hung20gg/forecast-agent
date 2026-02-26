#!/bin/bash
echo "=== Setting up Qdrant ==="

OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)
VERSION="v1.17.0"
BASE_URL="https://github.com/qdrant/qdrant/releases/download/${VERSION}"
FILE=""

if [[ "$OS" == *"mingw"* || "$OS" == *"msys"* || "$OS" == *"cygwin"* || "$OS" == *"windows"* ]]; then
    # Windows
    if [[ "$ARCH" == "x86_64" || "$ARCH" == "amd64" ]]; then
        FILE="qdrant-x86_64-pc-windows-msvc.zip"
    else
        echo "Unsupported architecture for Windows: $ARCH"
        exit 1
    fi
elif [[ "$OS" == *"darwin"* ]]; then
    # macOS
    if [[ "$ARCH" == "x86_64" || "$ARCH" == "amd64" ]]; then
        FILE="qdrant-x86_64-apple-darwin.tar.gz"
    elif [[ "$ARCH" == "arm64" || "$ARCH" == "aarch64" ]]; then
        FILE="qdrant-aarch64-apple-darwin.tar.gz"
    else
        echo "Unsupported architecture for macOS: $ARCH"
        exit 1
    fi
elif [[ "$OS" == *"linux"* ]]; then
    # Linux
    if [[ "$ARCH" == "x86_64" || "$ARCH" == "amd64" ]]; then
        FILE="qdrant-x86_64-unknown-linux-gnu.tar.gz"
    elif [[ "$ARCH" == "arm64" || "$ARCH" == "aarch64" ]]; then
        FILE="qdrant-aarch64-unknown-linux-musl.tar.gz"
    else
        echo "Unsupported architecture for Linux: $ARCH"
        exit 1
    fi
else
    echo "Unsupported OS: $OS"
    exit 1
fi

echo "Detected OS: $OS, Architecture: $ARCH"
echo "Downloading Qdrant version: $FILE..."

curl -L "$BASE_URL/$FILE" -o qdrant_download

mkdir -p qdrant

if [[ "$FILE" == *.zip ]]; then
    unzip -o qdrant_download -d qdrant
else
    tar -xzf qdrant_download -C qdrant
fi

rm qdrant_download
chmod +x qdrant/qdrant* 2>/dev/null
echo "Qdrant downloaded and prepared successfully."