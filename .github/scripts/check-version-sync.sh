#!/bin/bash
# Check VERSION and tag relationship

if [ ! -f VERSION ]; then
    exit 0
fi

FILE_VERSION=$(cat VERSION | tr -d '[:space:]')
LATEST_TAG=$(git describe --tags --abbrev=0 2>/dev/null | sed 's/^v//' || echo "0.0.0")

# Remove -dev suffix using parameter expansion
FILE_VERSION_BASE="${FILE_VERSION%-dev}"

# Remove 'v' prefix from tag using parameter expansion
LATEST_TAG="${LATEST_TAG#v}"

# Compare versions
if [ "$FILE_VERSION_BASE" = "$LATEST_TAG" ]; then
    # Exact match - this is a release state
    if [[ "$FILE_VERSION" == *"-dev" ]]; then
        echo "⚠️  VERSION shows $FILE_VERSION but tag exists for v$LATEST_TAG"
        echo "This seems wrong - either:"
        echo "  1. Remove -dev: echo '$LATEST_TAG' > VERSION"
        echo "  2. Bump to next version: echo 'X.Y.Z-dev' > VERSION"
        exit 1
    fi
    echo "✅ At release: v$FILE_VERSION (tag exists)"
    exit 0
elif [[ "$FILE_VERSION_BASE" > "$LATEST_TAG" ]]; then
    # VERSION ahead of tag - normal development
    echo "📝 Development mode: VERSION=$FILE_VERSION, latest tag=v$LATEST_TAG"
    exit 0
else
    # VERSION behind tag - something's wrong
    echo "❌ ERROR: VERSION ($FILE_VERSION) is behind latest tag (v$LATEST_TAG)"
    echo "VERSION should be ahead or equal, never behind!"
    exit 1
fi
