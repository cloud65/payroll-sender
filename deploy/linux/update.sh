#!/bin/bash
APP_DIR="/opt/report_parser"
VENV_DIR="$APP_DIR/.venv"
SERVICE="report_parser.service"
SERVICE_USER="report_parser"

cd "$APP_DIR" || exit 1

# Определяем текущую ветку
BRANCH=$(git rev-parse --abbrev-ref HEAD)

echo "🔍 Checking for updates in $BRANCH..."
git fetch origin "$BRANCH"

# Проверяем, есть ли новые коммиты
LOCAL=$(git rev-parse "$BRANCH")
REMOTE=$(git rev-parse "origin/$BRANCH")

if [ "$LOCAL" = "$REMOTE" ]; then
  echo "✅ No updates found. Everything is up to date."
  exit 0
fi

echo "⬇️  New version found. Pulling changes..."
git reset --hard "origin/$BRANCH"

echo "📦 Updating dependencies..."
source "$VENV_DIR/bin/activate"
pip install -r requirements.txt --quiet

chown -R $SERVICE_USER:$SERVICE_USER $APP_DIR

echo "🔄 Restarting service..."
sudo systemctl restart "$SERVICE"

echo "✅ Update complete!"