#!/bin/bash
# ================================================================
# Remembench — One-Command Deploy Script
# Usage: ./deploy.sh "optional commit message"
# ================================================================
set -e

VPS_USER="webapp"
VPS_HOST="187.77.4.109"
VPS_DIR="~/Remembench"
VPS_PASS="Mrmoose#291"
COMMIT_MSG="${1:-deploy: update $(date '+%Y-%m-%d %H:%M')}"

echo "🔄 [1/4] Committing and pushing local changes..."
git add -A
git diff --cached --quiet && echo "  (nothing new to commit)" || git commit -m "$COMMIT_MSG"
git push origin main
echo "✅ Pushed to GitHub"

echo ""
echo "🔄 [2/4] Pulling on VPS..."
sshpass -p "$VPS_PASS" ssh -o StrictHostKeyChecking=no ${VPS_USER}@${VPS_HOST} \
  "cd ${VPS_DIR} && git pull origin main"
echo "✅ VPS pulled latest code"

echo ""
echo "🔄 [3/4] Rebuilding Docker containers..."
sshpass -p "$VPS_PASS" ssh -o StrictHostKeyChecking=no ${VPS_USER}@${VPS_HOST} \
  "cd ${VPS_DIR} && echo '${VPS_PASS}' | sudo -S docker compose build && echo '${VPS_PASS}' | sudo -S docker compose up -d"
echo "✅ Containers rebuilt and restarted"

echo ""
echo "🔄 [4/4] Checking health..."
sleep 3
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://${VPS_HOST}/api/v1/health)
if [ "$STATUS" = "200" ]; then
  echo "✅ Health check passed (HTTP 200)"
else
  echo "⚠️  Health check returned HTTP $STATUS — check VPS logs"
fi

echo ""
echo "🔄 [5/5] Restarting Nginx to clear IP cache..."
sshpass -p "$VPS_PASS" ssh -o StrictHostKeyChecking=no ${VPS_USER}@${VPS_HOST} \
  "cd ${VPS_DIR} && echo '${VPS_PASS}' | sudo -S docker compose restart nginx"
echo "✅ Nginx restarted"

echo ""
echo "🚀 Deploy complete! App live at http://${VPS_HOST}/"
