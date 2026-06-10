#!/bin/bash
# Builds "Pero Portfolio.app" on the Desktop with your logo as the app icon.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_NAME="Pero Portfolio"
DESKTOP="${HOME}/Desktop"
APP_PATH="${DESKTOP}/${APP_NAME}.app"
ICON_PNG="${PROJECT_DIR}/static/compass-icon.png"

if [[ ! -f "${ICON_PNG}" ]]; then
  ICON_PNG="${PROJECT_DIR}/static/compass-logo.png"
fi
if [[ ! -f "${ICON_PNG}" ]]; then
  echo "Logo not found. Expected static/compass-icon.png or static/compass-logo.png"
  exit 1
fi

ICONSET="$(mktemp -d)/AppIcon.iconset"
mkdir -p "${ICONSET}"
for size in 16 32 128 256 512; do
  sips -z "${size}" "${size}" "${ICON_PNG}" --out "${ICONSET}/icon_${size}x${size}.png" >/dev/null
  s2=$((size * 2))
  sips -z "${s2}" "${s2}" "${ICON_PNG}" --out "${ICONSET}/icon_${size}x${size}@2x.png" >/dev/null
done
ICNS="$(mktemp).icns"
iconutil -c icns "${ICONSET}" -o "${ICNS}"

rm -rf "${APP_PATH}"
mkdir -p "${APP_PATH}/Contents/MacOS" "${APP_PATH}/Contents/Resources"

cat > "${APP_PATH}/Contents/MacOS/launch" << 'LAUNCH'
#!/bin/bash
PROJECT_DIR="__PROJECT_DIR__"
cd "${PROJECT_DIR}" || exit 1

if curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8501" 2>/dev/null | grep -qE '200|30'; then
  open "http://127.0.0.1:8501"
  exit 0
fi

if command -v streamlit >/dev/null 2>&1; then
  STREAMLIT="streamlit"
elif [[ -x "${PROJECT_DIR}/.venv/bin/streamlit" ]]; then
  STREAMLIT="${PROJECT_DIR}/.venv/bin/streamlit"
else
  osascript -e 'display alert "Streamlit not found" message "Run: pip install -r requirements.txt"'
  exit 1
fi

nohup "${STREAMLIT}" run "${PROJECT_DIR}/app.py" \
  --server.headless true \
  --browser.gatherUsageStats false \
  >/tmp/pero-portfolio-streamlit.log 2>&1 &

for _ in $(seq 1 30); do
  sleep 1
  if curl -s -o /dev/null "http://127.0.0.1:8501" 2>/dev/null; then
    break
  fi
done
open "http://127.0.0.1:8501"
LAUNCH

sed -i '' "s|__PROJECT_DIR__|${PROJECT_DIR}|g" "${APP_PATH}/Contents/MacOS/launch"
chmod +x "${APP_PATH}/Contents/MacOS/launch"
cp "${ICNS}" "${APP_PATH}/Contents/Resources/AppIcon.icns"

cat > "${APP_PATH}/Contents/Info.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleExecutable</key><string>launch</string>
  <key>CFBundleIdentifier</key><string>com.pero.portfolio</string>
  <key>CFBundleName</key><string>Pero Portfolio</string>
  <key>CFBundleDisplayName</key><string>Pero Portfolio</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>LSMinimumSystemVersion</key><string>10.13</string>
  <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
PLIST

rm -f "${ICNS}"
rm -rf "${ICONSET}"

echo "Created: ${APP_PATH}"
echo "Double-click to start, or drag into the Dock / Applications folder."
