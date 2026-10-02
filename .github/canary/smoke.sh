#!/usr/bin/env bash
# Contract smoke for the CI canary: CORS, retired endpoints, identity 401s.
# Checks only; no secrets are read or printed.
set -uo pipefail
API="${API:-http://127.0.0.1:7860}"
ORIGIN="${ORIGIN:-https://capomatic.vercel.app}"
fail=0

check() {
  if [ "$3" = "$2" ]; then echo "PASS  $1 ($3)"; else echo "FAIL  $1 expected=[$2] actual=[$3]"; fail=1; fi
}
code() { curl -s -o /dev/null -w '%{http_code}' "$@"; }
allow_origin() {
  curl -s -o /dev/null -D - -X OPTIONS "$API/detect" \
    -H "Origin: $1" -H "Access-Control-Request-Method: POST" \
    | tr -d '\r' | awk -F': ' 'tolower($1)=="access-control-allow-origin"{print $2}'
}

check "GET /health" 200 "$(code "$API/health")"
check "preflight allows $ORIGIN" "$ORIGIN" "$(allow_origin "$ORIGIN")"
check "preflight rejects foreign origin" "" "$(allow_origin "https://evil.example.com")"
check "GET /api/auth/admin-test retired" 410 "$(code "$API/api/auth/admin-test")"
check "GET /api/admin/users retired" 410 "$(code "$API/api/admin/users")"
check "POST /detect/refine retired" 410 "$(code -X POST -F detection_id=ci-smoke "$API/detect/refine")"
check "GET /api/auth/me without token" 401 "$(code "$API/api/auth/me")"
check "GET /api/auth/me malformed token" 401 "$(code -H 'Authorization: Bearer not-a-jwt' "$API/api/auth/me")"
echo "malformed-token body: $(curl -s -H 'Authorization: Bearer not-a-jwt' "$API/api/auth/me")"
exit $fail
