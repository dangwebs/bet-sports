#!/usr/bin/env bash
# scripts/setup-hooks.sh
# Script to install git hooks.

HOOK_DIR=".git/hooks"
PRE_PUSH_HOOK="$HOOK_DIR/pre-push"

if [ ! -d ".git" ]; then
    echo "❌ Error: .git directory not found. Are you in the root of the repository?"
    exit 1
fi

echo "Installing pre-push hook..."

cat <<EOF > "$PRE_PUSH_HOOK"
#!/usr/bin/env bash
# .git/hooks/pre-push
# This hook runs before git push.

echo "🚀 Running pre-push validation script..."
./scripts/validate_and_fix.sh
EOF

chmod +x "$PRE_PUSH_HOOK"

echo "✅ Pre-push hook installed successfully."
echo "Now your code will be validated before every push."
