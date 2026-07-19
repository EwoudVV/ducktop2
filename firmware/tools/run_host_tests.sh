#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
BUILD_DIR=${TMPDIR:-/tmp}/ducktop2-firmware-host-tests
CC_BIN=${CC:-cc}

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

COMMON_FLAGS="-std=c11 -Wall -Wextra -Wpedantic -Werror"

"$CC_BIN" $COMMON_FLAGS \
    -I"$ROOT/ec/include" \
    "$ROOT/ec/src/ec_policy.c" \
    "$ROOT/tests/test_ec_policy.c" \
    -o "$BUILD_DIR/ec_policy_tests"

"$CC_BIN" $COMMON_FLAGS \
    -I"$ROOT/ec/include" \
    "$ROOT/ec/src/ec_commit.c" \
    "$ROOT/tests/test_ec_commit.c" \
    -o "$BUILD_DIR/ec_commit_tests"

"$CC_BIN" $COMMON_FLAGS \
    -I"$ROOT/maker/include" \
    "$ROOT/maker/src/maker_policy.c" \
    "$ROOT/tests/test_maker_policy.c" \
    -o "$BUILD_DIR/maker_policy_tests"

"$BUILD_DIR/ec_policy_tests"
"$BUILD_DIR/ec_commit_tests"
"$BUILD_DIR/maker_policy_tests"
python3 "$ROOT/tools/verify_release_contract.py"

printf '%s\n' "host tests: PASS ($CC_BIN)"
