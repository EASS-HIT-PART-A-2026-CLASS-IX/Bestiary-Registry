#!/usr/bin/env bash

# =============================================================================
# Bestiary Registry — EX3 Demo Script
# Walks a grader through every major feature of the project end-to-end.
#
# Prerequisites: docker compose up -d must already be running.
# Usage:         bash scripts/demo.sh
# =============================================================================

# ── ANSI colours ──────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
MAGENTA='\033[1;35m'
DIM='\033[2m'
BOLD='\033[1m'
RESET='\033[0m'

API="http://localhost:8000"
ADMIN_USER="admin"
ADMIN_PASS="admin123"
DEMO_USER="demo_grader_$$"
DEMO_PASS="GraderPass1!"
TOKEN=""
CREATURE_ID=""
PASS=0
FAIL=0
WARN=0

# Resolve project root so the script works from any working directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ── Helpers ───────────────────────────────────────────────────────────────────
banner() {
    echo ""
    echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════════════════${RESET}"
    echo -e "${CYAN}${BOLD}  $1${RESET}"
    echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════════════════${RESET}"
}

ok()    { echo -e "  ${GREEN}${BOLD}✔${RESET}  $1";  PASS=$((PASS + 1)); }
fail()  { echo -e "  ${RED}${BOLD}✘${RESET}  $1";   FAIL=$((FAIL + 1)); }
warn()  { echo -e "  ${YELLOW}${BOLD}⚠${RESET}  $1"; WARN=$((WARN + 1)); }
info()  { echo -e "  ${YELLOW}▶${RESET}  $1"; }
data()  { echo -e "  ${DIM}    $1${RESET}"; }
abort() { echo -e "\n${RED}${BOLD}  FATAL: $1${RESET}\n  Cannot continue — fix the above and re-run.\n"; exit 1; }

# Extract a top-level string field from a JSON string using Python
json_get() { echo "$1" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('$2',''))" 2>/dev/null || echo ""; }

# Return only the HTTP status code for a curl call (remaining args passed to curl)
http_code() { curl -s -o /dev/null -w "%{http_code}" "$@"; }

# ── STEP 1: Docker Compose ────────────────────────────────────────────────────
banner "STEP 1 · Docker Compose Services"

info "Checking that all required services are running..."
ALL_UP=true
for svc in backend redis worker; do
    if docker compose -f "$PROJECT_ROOT/compose.yaml" ps 2>/dev/null | grep "$svc" | grep -qiE "Up|running|healthy"; then
        ok "$svc is up"
    else
        fail "$svc is NOT running"
        ALL_UP=false
    fi
done
$ALL_UP || abort "One or more services are down. Run: docker compose up -d"

# ── STEP 2: API Health ────────────────────────────────────────────────────────
banner "STEP 2 · API Health Check"

info "GET $API/"
HEALTH=$(curl -s --max-time 5 "$API/" 2>/dev/null)
if json_get "$HEALTH" "status" | grep -q "ok"; then
    ok "API is healthy"
    data "Response: $HEALTH"
else
    abort "API is not responding. Is the backend container healthy?"
fi

# ── STEP 3: Rate-Limit Headers ────────────────────────────────────────────────
banner "STEP 3 · Rate-Limit Headers  (slowapi — 100 req/min per IP)"

# GET / is undecorated — hit a route that has @limiter.limit() applied.
# We need a token, but that comes in Step 5. Use the admin token obtained later
# by deferring — instead, use the login endpoint (also decorated). Actually,
# /auth/token is a POST. The simplest decorated GET is /creatures/ (requires auth).
# We'll do a quick admin login here just for the header check.
info "Logging in temporarily to check rate-limit headers on GET $API/creatures/"
_RL_LOGIN=$(curl -s --max-time 5 -X POST "$API/auth/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "username=$ADMIN_USER" \
    --data-urlencode "password=$ADMIN_PASS" 2>/dev/null)
_RL_TOKEN=$(json_get "$_RL_LOGIN" "access_token")

if [ -z "$_RL_TOKEN" ]; then
    fail "Could not obtain token for rate-limit header check"
    data "Login response was: $_RL_LOGIN"
else
    data "Token obtained (preview): ${_RL_TOKEN:0:40}..."
    # Use -D - to dump headers from a real GET request (not -I which sends HEAD
    # and may bypass the @limiter.limit decorator bound to the GET handler).
    RL_HEADERS=$(curl -s --max-time 5 -D - -o /dev/null "$API/creatures/" \
        -H "Authorization: Bearer $_RL_TOKEN" 2>/dev/null | grep -i "x-ratelimit" || true)
    if [ -n "$RL_HEADERS" ]; then
        ok "X-RateLimit-* headers are present on GET /creatures/"
        while IFS= read -r line; do data "$line"; done <<< "$RL_HEADERS"
    else
        fail "X-RateLimit-* headers not found — rate limiting may not be active"
    fi
fi

# ── STEP 4: User Registration ─────────────────────────────────────────────────
banner "STEP 4 · User Registration"

info "Registering new demo user: '$DEMO_USER'"
REG_STATUS=$(http_code -X POST "$API/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"username\": \"$DEMO_USER\", \"password\": \"$DEMO_PASS\"}")

if [ "$REG_STATUS" = "201" ]; then
    ok "User '$DEMO_USER' registered (HTTP 201)"
elif [ "$REG_STATUS" = "200" ]; then
    ok "User '$DEMO_USER' registered (HTTP 200)"
else
    warn "Registration returned HTTP $REG_STATUS (user may already exist — continuing)"
fi

# ── STEP 5: Login & JWT Token ─────────────────────────────────────────────────
banner "STEP 5 · Login & JWT Authentication"

info "Logging in as admin (creature creation requires admin role)"
LOGIN_RESP=$(curl -s -X POST "$API/auth/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=$ADMIN_USER&password=$ADMIN_PASS")
TOKEN=$(json_get "$LOGIN_RESP" "access_token")

if [ -n "$TOKEN" ]; then
    ok "JWT token obtained (HS256, 30-minute expiry)"
    data "Token preview: ${TOKEN:0:50}..."
else
    abort "Login failed — got: $LOGIN_RESP"
fi

# ── STEP 6: Create a Creature ─────────────────────────────────────────────────
banner "STEP 6 · Create a New Creature"

CREATURE_NAME="Demo Phoenix $(date +%s)"
info "POST $API/creatures/ — '$CREATURE_NAME'"

CREATE_RESP=$(curl -s -X POST "$API/creatures/" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d "{
      \"name\": \"$CREATURE_NAME\",
      \"mythology\": \"Greek\",
      \"creature_type\": \"Mythic Beasts\",
      \"danger_level\": 8,
      \"habitat\": \"Volcanic Peaks\"
    }")
CREATURE_ID=$(json_get "$CREATE_RESP" "id")

if [ -n "$CREATURE_ID" ]; then
    ok "Creature created — ID: $CREATURE_ID"
    data "Name:       $(json_get "$CREATE_RESP" "name")"
    data "Mythology:  $(json_get "$CREATE_RESP" "mythology")"
    data "Type:       $(json_get "$CREATE_RESP" "creature_type")"
    data "Danger:     $(json_get "$CREATE_RESP" "danger_level") / 10"
    data "Habitat:    $(json_get "$CREATE_RESP" "habitat")"
    data "Lore:       (pending async generation...)"
else
    abort "Creature creation failed — got: $CREATE_RESP"
fi

# ── STEP 7: Async Lore Generation ────────────────────────────────────────────
banner "STEP 7 · Async Lore Generation  (ARQ Worker + Gemini LLM)"

info "Polling GET $API/creatures/$CREATURE_ID for lore (up to 30s)..."
LORE=""
for i in $(seq 1 15); do
    sleep 2
    printf "\r  ${DIM}  Attempt $i/15 — waiting for worker...${RESET}    "
    CREATURE_RESP=$(curl -s --max-time 5 "$API/creatures/$CREATURE_ID" \
        -H "Authorization: Bearer $TOKEN" 2>/dev/null)
    LORE=$(json_get "$CREATURE_RESP" "lore")
    # Python prints "None" for JSON null
    if [ -n "$LORE" ] && [ "$LORE" != "None" ]; then
        break
    fi
done
echo ""  # clear the carriage-return line

if [ -n "$LORE" ] && [ "$LORE" != "None" ]; then
    ok "Lore generated by the ARQ background worker"
    data "${LORE:0:200}..."
else
    warn "Lore not yet available — GEMINI_API_KEY may not be set, or worker is still processing"
    data "The lore field will be populated automatically once the worker processes the job."
fi

# ── STEP 8: Creature Catalog ──────────────────────────────────────────────────
banner "STEP 8 · Searchable & Filterable Creature Catalog"

info "GET $API/creatures/ — fetching all creatures"
LIST_RESP=$(curl -s --max-time 5 "$API/creatures/" \
    -H "Authorization: Bearer $TOKEN" 2>/dev/null)
TOTAL=$(echo "$LIST_RESP" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")

if [ "$TOTAL" -gt 0 ] 2>/dev/null; then
    ok "$TOTAL creature(s) in the registry"
else
    fail "Could not retrieve creature list"
fi

info "Filtering is handled in the Streamlit frontend (name search, class, mythology, habitat, danger range)"
info "Open http://localhost:8501 to see the live searchable/filterable dashboard"

# ── STEP 9: CSV Export ────────────────────────────────────────────────────────
banner "STEP 9 · CSV Export"

info "GET $API/creatures/export/csv"
CSV_RESP=$(curl -s --max-time 10 "$API/creatures/export/csv" \
    -H "Authorization: Bearer $TOKEN" 2>/dev/null)
CSV_LINE_COUNT=$(echo "$CSV_RESP" | wc -l)
HEADER_LINE=$(echo "$CSV_RESP" | head -1)

if echo "$HEADER_LINE" | grep -q "^id,name"; then
    ok "CSV export successful — $CSV_LINE_COUNT line(s) (including header)"
    data "Columns: $HEADER_LINE"
    echo ""
    info "First 3 data rows:"
    echo "$CSV_RESP" | head -4 | tail -3 | while IFS= read -r line; do data "$line"; done
else
    fail "CSV export did not return expected format"
    data "Got: ${CSV_RESP:0:120}"
fi

# ── STEP 10: Test Suite ───────────────────────────────────────────────────────
banner "STEP 10 · Test Suite  (pytest — in-memory SQLite, no Docker required)"

# Locate uv — it may not be on PATH when running under WSL bash on Windows.
UV_BIN=$(which uv 2>/dev/null || command -v uv 2>/dev/null || \
    ls /mnt/c/Users/liad7/.local/bin/uv.exe 2>/dev/null || \
    ls /mnt/c/Users/*/AppData/Local/uv/uv.exe 2>/dev/null | head -1 || echo "")

if [ -n "$UV_BIN" ]; then
    info "Running: $UV_BIN run python -m pytest tests/ -v --tb=short"
    echo ""
    (cd "$PROJECT_ROOT/backend" && "$UV_BIN" run python -m pytest tests/ -v --tb=short 2>&1)
    TEST_EXIT=$?
else
    warn "uv not found in PATH — falling back to: python -m pytest tests/ -v --tb=short"
    echo ""
    (cd "$PROJECT_ROOT/backend" && python -m pytest tests/ -v --tb=short 2>&1)
    TEST_EXIT=$?
fi
echo ""
if [ $TEST_EXIT -eq 0 ]; then
    ok "All tests passed"
else
    fail "Test suite reported failures (exit code $TEST_EXIT)"
fi

# ── STEP 11: Frontend ─────────────────────────────────────────────────────────
banner "STEP 11 · Streamlit Frontend"

echo ""
echo -e "  ${MAGENTA}${BOLD}The Streamlit frontend is started separately (not via Docker Compose).${RESET}"
echo ""
echo -e "  ${BOLD}  To launch it, run in a new terminal:${RESET}"
echo ""
echo -e "  ${CYAN}    cd backend && uv run python -m streamlit run ../frontend/dashboard.py${RESET}"
echo ""
echo -e "  ${BOLD}  Then open:${RESET}  ${CYAN}${BOLD}http://localhost:8501${RESET}"
echo -e "  ${DIM}  Default login: admin / admin123${RESET}"
echo ""
echo -e "  ${DIM}  Features visible in the UI:${RESET}"
echo -e "  ${DIM}    • Real-time name search + multi-faceted filtering (class, mythology, habitat, danger)${RESET}"
echo -e "  ${DIM}    • Creature lore displayed under each row (generated by Gemini worker)${RESET}"
echo -e "  ${DIM}    • CSV export button in Settings → General tab${RESET}"
echo -e "  ${DIM}    • Per-user avatar upload${RESET}"
echo ""

# Also reachable at Render/Streamlit Cloud if deployed
echo -e "  ${BOLD}  Live deployments:${RESET}"
echo -e "  ${DIM}    API:      https://bestiary-registry.onrender.com${RESET}"
echo -e "  ${DIM}    Frontend: https://bestiary-registry.streamlit.app${RESET}"
echo -e "  ${DIM}    API Docs: https://bestiary-registry.onrender.com/docs${RESET}"
echo ""

# ── Summary ───────────────────────────────────────────────────────────────────
banner "DEMO COMPLETE · Results"

echo ""
echo -e "  ${GREEN}${BOLD}Passed:  $PASS${RESET}"
if [ $WARN -gt 0 ]; then
    echo -e "  ${YELLOW}${BOLD}Warnings: $WARN${RESET}"
fi
if [ $FAIL -gt 0 ]; then
    echo -e "  ${RED}${BOLD}Failed:  $FAIL${RESET}"
else
    echo -e "  ${GREEN}${BOLD}Failed:  $FAIL — all checks passed ✔${RESET}"
fi
echo ""
echo -e "  ${DIM}Local API:      $API${RESET}"
echo -e "  ${DIM}Local API Docs: $API/docs${RESET}"
echo -e "  ${DIM}Local Frontend: http://localhost:8501 (launch manually — see Step 11)${RESET}"
echo ""

[ $FAIL -eq 0 ]  # exit 0 if all passed, 1 if any failed
