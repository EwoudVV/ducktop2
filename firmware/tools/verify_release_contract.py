#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ERRORS: list[str] = []


def require(condition: bool, message: str) -> None:
    if not condition:
        ERRORS.append(message)


def read_text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def read_csv(relative: str) -> list[dict[str, str]]:
    with (ROOT / relative).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def verify_unique_ids(rows: list[dict[str, str]], label: str) -> None:
    ids = [row.get("id", "") for row in rows]
    require(all(ids), f"{label}: every row needs an id")
    require(len(ids) == len(set(ids)), f"{label}: ids must be unique")


version = read_text("VERSION").strip()
require(bool(re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+-[a-z0-9.-]+", version)),
        "VERSION must use x.y.z-suffix format")

cmake = read_text("CMakeLists.txt")
readme = read_text("README.md")
release_readme = read_text("release/README.md")
require("/VERSION\" DUCKTOP2_FIRMWARE_VERSION" in cmake,
        "CMake must read firmware/VERSION")
require(f'VERSION="${{DUCKTOP2_FIRMWARE_VERSION}}"' in cmake,
        "CMake compile definition must use the loaded version")
require(f"Version: `{version}`" in readme, "README version is stale")
require(f"Version: `{version}`" in release_readme,
        "release README version is stale")

policy_header = read_text("ec/include/ducktop2/ec/ec_policy.h")
policy_source = read_text("ec/src/ec_policy.c")
commit_header = read_text("ec/include/ducktop2/ec/ec_commit.h")
commit_source = read_text("ec/src/ec_commit.c")
telemetry_header = read_text("ec/include/ducktop2/ec/ec_telemetry.h")
telemetry_source = read_text("ec/src/ec_telemetry.c")
maker_header = read_text("maker/include/ducktop2/maker/maker_policy.h")
maker_source = read_text("maker/src/maker_policy.c")

required_policy_tokens = {
    "15 W low-pack ceiling":
        "EC_DEFAULT_LOW_PACK_MU_EDP_BUDGET_MW 15000u",
    "6 W platform reserve": "EC_DEFAULT_SYSTEM_RESERVE_MW 6000u",
    "85 percent source model":
        "EC_DEFAULT_SOURCE_EFFICIENCY_PERMILLE 850u",
    "reset interlock fault": "EC_FAULT_RESET_INTERLOCK",
    "service bus fault": "EC_FAULT_SERVICE_BUS",
    "power policy acknowledgement": "power_limits_applied",
    "pack telemetry validity": "pack_telemetry_valid",
    "two PD ports": "EC_PD_PORT_COUNT 2u",
    "four source states": "EC_SOURCE_COUNT 4u",
    "optional radio request": "request_radio_db",
    "optional radio output": "radio_db_power_enable",
}
for label, token in required_policy_tokens.items():
    require(token in policy_header, f"policy missing {label}")

for token in (
    "reset_interlock_ready",
    "EC_FAULT_POWER_POLICY_APPLY_TIMEOUT",
    "EC_FAULT_MU_POWER_GOOD_STUCK_HIGH",
    "source_input_power_mw",
    "ec_policy_usable_power_mw",
    "!controller->path_commanded && !inputs->all_pd_paths_off",
    "apply_radio_db_policy",
    "radio_db_request_blocked",
    "radio_db_power_good_timeout_ms",
):
    require(token in policy_source, f"policy source missing {token}")

validating_source = policy_source[
    policy_source.index("static void step_validating"):
    policy_source.index("static void apply_load_policy")
]
bootstrap_path_token = (
    "controller->outputs.pd_path_enable[pd_index(source)] = true;"
)
iindpm_command_token = (
    "controller->outputs.charger_iindpm_ma = expected_iindpm_ma;"
)
require(bootstrap_path_token in validating_source,
        "PD validation must contain a path-only bootstrap command")
require(iindpm_command_token in validating_source,
        "PD validation must contain the post-path IINDPM command")
if (bootstrap_path_token in validating_source and
        iindpm_command_token in validating_source):
    require(validating_source.index(bootstrap_path_token) <
            validating_source.index(iindpm_command_token),
            "PD validation must bootstrap the qualified path before IINDPM")

for token in (
    "ec_commit_force_safe",
    "ec_commit_apply",
    "EC_COMMIT_SAFE_STATE_IO_ERROR",
):
    require(token in commit_header, f"commit interface missing {token}")
require("write_safe_sequence" in commit_source,
        "commit source missing safe-state rollback")
require("EC_COMMIT_CHARGER_IINDPM_MA" in commit_source and
        "EC_COMMIT_PD1_PATH_ENABLE" in commit_source,
        "commit source missing IINDPM/path ordering commands")
require("current_path_enabled && desired_path_enabled" in commit_source,
        "commit adapter must reject direct source-to-source changes")
require("path_changed && desired->charger_iindpm_ma != 0u" in commit_source,
        "commit adapter must reject an unstaged powered-path request")
require("test_path_bootstrap_precedes_iindpm_ack" in
        read_text("tests/test_ec_policy.c"),
        "policy tests must cover adapter-only PD bootstrap ordering")
require("test_unstaged_powered_path_is_rejected" in
        read_text("tests/test_ec_commit.c"),
        "commit tests must reject unstaged powered-path requests")
require("test_optional_radio_daughterboard_is_isolated" in
        read_text("tests/test_ec_policy.c"),
        "policy tests must prove radio-board absence isolation")
require("test_radio_daughterboard_power_good_timeout" in
        read_text("tests/test_ec_policy.c"),
        "policy tests must cover radio-board power-good timeout")
require("test_radio_daughterboard_stuck_good_and_reset_fail_off" in
        read_text("tests/test_ec_policy.c"),
        "policy tests must cover radio-board stuck-good and reset fail-off")

for label, token in {
    "PD1 7-bit target address":
        "EC_PD1_TCPC_I2C_ADDRESS_7BIT 0x20u",
    "PD2 7-bit target address":
        "EC_PD2_TCPC_I2C_ADDRESS_7BIT 0x21u",
    "PD1 service-mux channel": "EC_PD1_SERVICE_MUX_CHANNEL 2u",
    "PD2 service-mux channel": "EC_PD2_SERVICE_MUX_CHANNEL 3u",
    "battery snapshot helper": "ec_telemetry_build_snapshot",
    "active input telemetry": "EC_TELEMETRY_VALID_ACTIVE_INPUT",
    "charge power telemetry": "charge_power_mw",
    "discharge power telemetry": "discharge_power_mw",
}.items():
    require(token in telemetry_header or token in telemetry_source,
            f"telemetry model missing {label}")
require("temperature" not in telemetry_header.lower(),
        "OLED telemetry model must not expose pack temperature")

for token in (
    "hardware_interlock_ready",
    "user_power_authorized",
    "user_io_authorized",
    "MAKER_FAULT_INTERLOCK",
    "MAKER_FAULT_IO_AUTHORIZATION",
):
    require(token in maker_header, f"maker policy missing {token}")
require("any_io_requested" in maker_source,
        "maker policy source must reject queued unauthorized I/O")

ec_vectors = read_csv("tests/vectors/ec_policy_vectors.csv")
maker_vectors = read_csv("tests/vectors/maker_policy_vectors.csv")
verify_unique_ids(ec_vectors, "EC vectors")
verify_unique_ids(maker_vectors, "maker vectors")
ec_ids = {row["id"] for row in ec_vectors}
maker_ids = {row["id"] for row in maker_vectors}
require({"EC-BOOT-001", "EC-PD-001", "EC-PWR-001", "EC-PWR-002",
         "EC-PWR-003", "EC-XFER-001", "EC-LOW-001", "EC-LOW-002",
         "EC-LOW-004", "EC-MUPG-001", "EC-AUX-001", "EC-AUX-002",
         "EC-AUX-003"}.issubset(ec_ids),
        "EC vectors are missing required release cases")
require({"MK-BOOT-001", "MK-INT-001", "MK-AUTH-001", "MK-WDG-001"}
        .issubset(maker_ids),
        "maker vectors are missing required release cases")
low_stimuli = {row["stimulus"] for row in ec_vectors
               if row["id"].startswith("EC-LOW-")}
require("pack_low_request_15000mW" in low_stimuli,
        "EC vectors must cover the accepted 15 W low-pack point")
require("pack_low_request_15001mW" in low_stimuli,
        "EC vectors must reject a request above 15 W")
maker_by_id = {row["id"]: row for row in maker_vectors}
require(maker_by_id.get("MK-PWR-001", {}).get("expected_fault") ==
        "USER_POWER",
        "maker vectors must reject an unauthorized rail request")
require(maker_by_id.get("MK-IO-001", {}).get("expected_fault") ==
        "IO_AUTHORIZATION",
        "maker vectors must reject an unauthorized I/O request")
require("pack_low_pack_only_false_request_15000mW" in low_stimuli,
        "low-pack limiting must not depend on the legacy pack_only flag")
for relative in (
    "ec/include/ducktop2/ec/ec_policy.h",
    "tests/test_ec_policy.c",
    "tests/vectors/ec_policy_vectors.csv",
    "README.md",
    "release/README.md",
    "release/hil_matrix.csv",
):
    contract_text = read_text(relative)
    require("18000" not in contract_text and "18 W" not in contract_text and
            "24000" not in contract_text and "24 W" not in contract_text,
            f"{relative}: stale low-pack contract")

for relative in (
    "ec/include/ducktop2/ec/ec_policy.h",
    "ec/include/ducktop2/ec/ec_commit.h",
    "ec/src/ec_policy.c",
    "ec/src/ec_commit.c",
    "tests/test_ec_policy.c",
    "tests/test_ec_commit.c",
    "tests/vectors/ec_policy_vectors.csv",
    "README.md",
    "release/README.md",
    "release/hil_matrix.csv",
):
    contract_text = read_text(relative)
    require("PD3" not in contract_text and "pd3" not in contract_text,
            f"{relative}: stale third PD path")
    require("radio_vhf" not in contract_text and
            "radio_uhf" not in contract_text and
            "RADIO_VHF" not in contract_text and
            "RADIO_UHF" not in contract_text,
            f"{relative}: stale split radio controls")
for relative in (
    "ec/include/ducktop2/ec/ec_telemetry.h",
    "tests/test_ec_telemetry.c",
    "README.md",
    "release/README.md",
    "release/hil_matrix.csv",
):
    contract_text = read_text(relative)
    require("0x40" not in contract_text and "0x41" not in contract_text,
            f"{relative}: shifted TPS25751A address used as 7-bit address")

hil_rows = read_csv("release/hil_matrix.csv")
verify_unique_ids(hil_rows, "HIL matrix")
required_hil = {
    "PROG-EC-001", "PROG-MK-001", "EC-BOOT-001", "EC-NRST-001",
    "EC-WDG-001", "EC-BROWN-001", "EC-SVC-001", "EC-I2C-001",
    "EC-PD1-001", "EC-PD2-001", "EC-PD-INVALID-001",
    "EC-PD-COLD-001", "EC-PD-5V-001",
    "EC-PD-SVC-001",
    "EC-IINDPM-ACK-001", "EC-IINDPM-MISMATCH-001",
    "EC-COMMIT-FAIL-001", "EC-PD-DROP-001", "EC-PD-FAULT-001",
    "EC-XFER-001", "EC-PATH-PG-001", "EC-MU-PG-001", "EC-MU-PG-002",
    "EC-CHG-FAULT-001", "EC-THERM-001", "EC-PWRLIM-001",
    "EC-LOW-001", "EC-LOW-002", "EC-LOW-ACK-001", "EC-TRIP-001",
    "EC-RECOVER-001", "EC-RADIO-ABSENT-001", "EC-RADIO-PG-001",
    "EC-RADIO-FAULT-001", "EC-OLED-TLM-001",
    "MK-BOOT-001", "MK-RUN-001", "MK-BOOTSEL-001",
    "MK-WDG-001", "MK-PWR-FAULT-001", "MK-AUTH-001", "MK-GPIO-001",
}
require(required_hil.issubset({row["id"] for row in hil_rows}),
        "HIL matrix is missing required qualification rows")
for row in hil_rows:
    status = row.get("status", "")
    require(status in {"NOT_RUN", "PASS", "FAIL", "BLOCKED"},
            f"{row.get('id')}: invalid HIL status {status!r}")
    if status == "PASS":
        evidence = ROOT / row.get("evidence_path", "")
        expected_hash = row.get("evidence_sha256", "")
        require(evidence.is_file(), f"{row['id']}: PASS evidence is missing")
        require(bool(re.fullmatch(r"[0-9a-f]{64}", expected_hash)),
                f"{row['id']}: PASS evidence hash is invalid")
        if evidence.is_file() and expected_hash:
            actual_hash = hashlib.sha256(evidence.read_bytes()).hexdigest()
            require(actual_hash == expected_hash,
                    f"{row['id']}: PASS evidence hash mismatch")

target_binaries = [path for path in (ROOT / "release").rglob("*")
                   if path.suffix.lower() in {".bin", ".elf", ".uf2"}]
require(not target_binaries,
        "unqualified target binaries must not be stored in release/")

manifest = hashlib.sha256()
for path in sorted(ROOT.rglob("*")):
    if not path.is_file() or "build" in path.parts or "__pycache__" in path.parts:
        continue
    relative = path.relative_to(ROOT).as_posix()
    manifest.update(relative.encode("utf-8") + b"\0")
    manifest.update(hashlib.sha256(path.read_bytes()).digest())

if ERRORS:
    for error in ERRORS:
        print(f"release contract: FAIL: {error}", file=sys.stderr)
    raise SystemExit(1)

print(f"release contract: PASS ({version})")
print(f"firmware manifest: {manifest.hexdigest()}")
print(f"HIL status: {len(hil_rows)} rows; "
      f"{sum(row['status'] == 'NOT_RUN' for row in hil_rows)} NOT_RUN")
