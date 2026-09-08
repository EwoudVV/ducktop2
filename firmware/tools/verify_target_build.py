#!/usr/bin/env python3
"""Check register definitions, dependency hashes and linked interrupt vectors."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(args):
    return subprocess.check_output(list(map(str, args)), text=True, stderr=subprocess.STDOUT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    compiler = shutil.which("arm-none-eabi-gcc")
    if compiler is None:
        raise RuntimeError("arm-none-eabi-gcc is required for the target register check")
    vendor = ROOT / "vendor"
    sources = json.loads((vendor / "sources.json").read_text())
    for name, source in sources.items():
        for rel, digest in source["files"].items():
            actual = hashlib.sha256((vendor / name / rel).read_bytes()).hexdigest()
            if actual != digest:
                raise ValueError(f"changed dependency: {name}/{rel}")
    flags = [compiler, "-mcpu=cortex-m4", "-mthumb", "-mfpu=fpv4-sp-d16", "-mfloat-abi=hard",
             "-std=c11", "-ffreestanding", "-nostdinc", "-Wall", "-Wextra", "-Werror", "-fsyntax-only",
             "-DSTM32F407xx", "-I" + str(ROOT / "ec_target"), "-I" + str(ROOT / "ec_target/include"),
             "-isystem", vendor / "cmsis-device-f4/Include",
             "-isystem", vendor / "cmsis-core/CMSIS/Core/Include", ROOT / "tests/test_target_registers.c"]
    run(flags)
    elf = args.elf.resolve()
    symbols = {}
    for line in run(["arm-none-eabi-nm", "-n", elf]).splitlines():
        match = re.fullmatch(r"([0-9a-fA-F]+)\s+(\S)\s+(\S+)", line.strip())
        if match:
            symbols[match[3]] = (int(match[1], 16), match[2])
    header = (vendor / "cmsis-device-f4/Include/stm32f407xx.h").read_text()
    irqs = {int(m[2]): m[1] + "_IRQHandler" for m in re.finditer(
        r"^\s*(\w+)_IRQn\s*=\s*(\d+)", header, re.M)}
    core = ["_estack", "Reset_Handler", "NMI_Handler", "HardFault_Handler", "MemManage_Handler",
            "BusFault_Handler", "UsageFault_Handler", None, None, None, None, "SVC_Handler",
            "DebugMon_Handler", None, "PendSV_Handler", "SysTick_Handler"]
    expected = core + [irqs.get(n) for n in range(max(irqs) + 1)]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=args.output.parent, prefix="vectors-") as tmp:
        binary = Path(tmp) / "vectors.bin"
        run(["arm-none-eabi-objcopy", "-O", "binary", "--only-section=.isr_vector", elf, binary])
        data = binary.read_bytes()
    if len(data) != 4 * len(expected):
        raise ValueError(f"vector table size {len(data)} does not match this device")
    stack = struct.unpack_from("<I", data)[0]
    if not 0x20000000 < stack <= 0x20020000 or stack % 8:
        raise ValueError(f"invalid initial stack pointer {stack:#x}")
    for index, name in enumerate(expected):
        value = struct.unpack_from("<I", data, 4 * index)[0]
        wanted = 0 if name is None else symbols[name][0] | (0 if index == 0 else 1)
        if value != wanted:
            raise ValueError(f"vector {index} {name}: {value:#x} != {wanted:#x}")
    for name in ("SysTick_Handler", "OTG_FS_IRQHandler", "EXTI9_5_IRQHandler"):
        if symbols[name][1].upper() != "T":
            raise ValueError(f"{name} still resolves to a weak default handler")
    result = {"register_layout": "PASS", "dependency_hashes": "PASS",
              "linked_vector_entries": len(expected), "device_irqs": len(irqs),
              "elf_sha256": hashlib.sha256(elf.read_bytes()).hexdigest(),
              "hardware_execution": "not performed"}
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
