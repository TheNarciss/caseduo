#!/usr/bin/env bash
# Screenshots of the app in the iOS simulator, so UI changes can be reviewed on a pull request
# without a Mac (same approach as SingaSmoke). Run by .github/workflows/ios.yml after the
# simulator build. Debug builds only: -uiDemo YES serves canned data, no network, no login.
#
#   ios/scripts/ci-screenshots.sh path/to/CaseDuo.app output-folder
set -euo pipefail

APP="${1:?path to CaseDuo.app}"
OUT="${2:-screenshots}"
BUNDLE_ID=uk.riskybusinesses.caseduo
mkdir -p "$OUT"

UDID=$(xcrun simctl list devices available -j | python3 -c '
import json, sys
devices = json.load(sys.stdin)["devices"]
phones = [(runtime, d) for runtime, ds in devices.items() if ".iOS-" in runtime
          for d in ds if d["name"].startswith("iPhone") and "Pro" in d["name"] and "Max" not in d["name"]]
phones.sort(key=lambda p: [int(x) for x in p[0].rsplit("iOS-", 1)[1].split("-")])
print(phones[-1][1]["udid"])')
echo "Simulator: $UDID"

xcrun simctl boot "$UDID" || true
xcrun simctl bootstatus "$UDID" -b
xcrun simctl install "$UDID" "$APP"
xcrun simctl ui "$UDID" appearance dark
xcrun simctl status_bar "$UDID" override --time 9:41 --dataNetwork wifi --wifiBars 3 \
  --cellularMode active --cellularBars 4 --batteryState charged --batteryLevel 100

# shoot NAME SECONDS [launch arguments…]
shoot() {
  local name=$1 wait=$2
  shift 2
  xcrun simctl terminate "$UDID" "$BUNDLE_ID" 2>/dev/null || true
  # shellcheck disable=SC2086
  xcrun simctl launch "$UDID" "$BUNDLE_ID" -uiDemo YES "$@" >/dev/null
  sleep "$wait"
  xcrun simctl io "$UDID" screenshot "$OUT/$name.png" >/dev/null 2>&1
  echo "✓ $name"
}

SET="${SHOT_SET:-quick}"
shoot 01-today 6
shoot 02-exercise 6 -uiOpen exercise
shoot 03-result 9 -uiOpen result
shoot 04-history 6 -uiTab history
[ "$SET" = full ] && shoot 05-league 6 -uiTab league
[ "$SET" = full ] && shoot 06-profile 6 -uiTab profile
[ "$SET" = full ] && shoot 07-day-close 6 -uiOpen dayclose
[ "$SET" = full ] && shoot 08-mock 6 -uiOpen mock

sips -Z 1200 "$OUT"/*.png >/dev/null
ls -la "$OUT"
