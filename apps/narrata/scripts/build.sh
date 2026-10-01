#!/usr/bin/env bash
# Build or test Narrata on the iOS simulator without code signing.
# Usage: scripts/build.sh build|test
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build

ACTION="${1:-build}"
DEST="platform=iOS Simulator,name=${SIM_NAME:-iPhone 17}"

# Pick the newest available iPhone simulator if the default name isn't present.
if ! xcrun simctl list devices available | grep -q "${SIM_NAME:-iPhone 17}"; then
  NAME=$(xcrun simctl list devices available | grep -o 'iPhone [^(]*' | sed 's/ *$//' | tail -1)
  DEST="platform=iOS Simulator,name=${NAME}"
fi
echo "Destination: $DEST"

COMMON=(-project Narrata.xcodeproj -scheme Narrata -destination "$DEST"
        CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO CODE_SIGN_IDENTITY=""
        -derivedDataPath build/DerivedData)

set -o pipefail
if [ "$ACTION" = "test" ]; then
  xcodebuild test "${COMMON[@]}" 2>&1 | tee build/test.log | grep -E "error:|warning: unre|Test Case|Executed|\*\* TEST" || true
  if ! grep -q "\*\* TEST SUCCEEDED \*\*" build/test.log; then
    echo "::group::install/launch diagnostics"
    grep -n -i -E "validate|NSExtension|XPC|Unable to Install|MIInstall|failed to install|error ?[:=]|reason|description" build/test.log | grep -v "warning:" | head -80
    APP=$(find build/DerivedData -path '*Debug-iphonesimulator/Narrata.app' -maxdepth 6 | head -1)
    echo "app: $APP"
    for plist in "$APP/Info.plist" "$APP"/PlugIns/*/Info.plist; do
      echo "--- $plist"; plutil -p "$plist" | head -60
    done
    echo "::endgroup::"
    exit 1
  fi
else
  xcodebuild build "${COMMON[@]}" 2>&1 | tee build/build.log | grep -E "error:|\*\* BUILD" || true
  grep -q "\*\* BUILD SUCCEEDED \*\*" build/build.log
fi
