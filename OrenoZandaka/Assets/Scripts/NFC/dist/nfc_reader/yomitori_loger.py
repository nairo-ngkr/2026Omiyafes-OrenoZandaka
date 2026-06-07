import argparse
from datetime import datetime
from pathlib import Path
import re
import sys
import time

import nfc
import nfc.clf
import nfc.tag
from nfc.tag.tt3 import BlockCode, ServiceCode
from nfc.tag.tt3_sony import activate as activate_sony_tag


TRANSIT_SYSTEM_CODE = 0x0003
STUDENT_SYSTEM_CANDIDATES = (0x8277,)
BALANCE_SERVICE_CODE = 0x008B
STUDENT_ID_SERVICE_CODE = 0x010B
MOBILE_SUICA_INFO_SERVICE = 0x188B


def infer_transport(tag: nfc.tag.Tag) -> str:
    module_name = tag.__class__.__module__
    if ".tt3" in module_name:
        return "felica"
    if ".tt4" in module_name:
        return "type4a"
    return "other"


def sanitize_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._") or "unknown_tag"


def get_tag_id(tag: nfc.tag.Tag) -> str:
    for attr in ("identifier", "_nfcid", "idm"):
        value = getattr(tag, attr, None)
        if isinstance(value, (bytes, bytearray)) and value:
            return value.hex().upper()
    return sanitize_filename(str(tag))


def normalize_tag(tag: nfc.tag.Tag) -> nfc.tag.Tag:
    if infer_transport(tag) != "felica":
        return tag

    try:
        sony_tag = activate_sony_tag(tag.clf, tag.target)
    except Exception:
        return tag

    return sony_tag or tag


def make_service_code(service_code: int) -> ServiceCode:
    return ServiceCode(service_code >> 6, service_code & 0x3F)


def format_block(data: bytes) -> str:
    hex_part = " ".join(f"{byte:02X}" for byte in data)
    text_part = "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in data)
    return f"{hex_part} |{text_part}|"


def activate_system(tag: nfc.tag.Tag, system_code: int) -> tuple[bool, str]:
    if not hasattr(tag, "polling"):
        return False, "tag has no polling()"

    try:
        idm, pmm = tag.polling(system_code)[:2]
    except Exception as exc:
        return False, str(exc)

    tag.idm = idm
    tag.pmm = pmm
    if hasattr(tag, "sys"):
        tag.sys = system_code
    return True, "ok"


def request_system_codes(tag: nfc.tag.Tag) -> tuple[list[int], str | None]:
    if not hasattr(tag, "request_system_code"):
        return [], "tag has no request_system_code()"

    try:
        return list(tag.request_system_code()), None
    except Exception as exc:
        return [], str(exc)


def search_service_code(tag: nfc.tag.Tag, service_index: int) -> tuple[int, ...] | None:
    if not hasattr(tag, "search_service_code"):
        return None

    try:
        return tag.search_service_code(service_index)
    except Exception:
        return None


def discover_services(tag: nfc.tag.Tag) -> dict[int, list[int]]:
    services_by_system: dict[int, list[int]] = {}
    systems, _ = request_system_codes(tag)

    original_idm = getattr(tag, "idm", None)
    original_pmm = getattr(tag, "pmm", None)
    original_sys = getattr(tag, "sys", None)

    for system_code in systems:
        ok, _ = activate_system(tag, system_code)
        if not ok:
            continue

        services: list[int] = []
        for service_index in range(256):
            result = search_service_code(tag, service_index)
            if result is None:
                break
            if len(result) == 1:
                services.append(result[0])
        services_by_system[system_code] = services

    if original_idm is not None:
        tag.idm = original_idm
    if original_pmm is not None:
        tag.pmm = original_pmm
    if original_sys is not None and hasattr(tag, "sys"):
        tag.sys = original_sys

    return services_by_system


def read_service_blocks(tag: nfc.tag.Tag, service_code: int, block_count: int) -> tuple[list[bytes] | None, str | None]:
    if not hasattr(tag, "read_without_encryption"):
        return None, "tag has no read_without_encryption()"

    service = make_service_code(service_code)
    blocks = [BlockCode(index, service=0) for index in range(block_count)]

    try:
        data = tag.read_without_encryption([service], blocks)
    except Exception as exc:
        return None, str(exc)

    return [data[index:index + 16] for index in range(0, len(data), 16)], None


def parse_transit_balance(block: bytes) -> int | None:
    if len(block) < 13:
        return None
    return int.from_bytes(block[11:13], byteorder="little")


def extract_student_id(blocks: list[bytes]) -> str | None:
    match = re.search(rb"[A-Z]{2}\d{5}", b"".join(blocks))
    if match:
        return match.group(0).decode("ascii")
    return None


def build_log(tag: nfc.tag.Tag) -> str:
    tag = normalize_tag(tag)
    lines: list[str] = []

    lines.append(f"captured_at: {datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"tag_type: {tag.__class__.__module__}.{tag.__class__.__name__}")
    lines.append(f"tag_repr: {tag}")
    lines.append(f"tag_id: {get_tag_id(tag)}")
    lines.append(f"transport: {infer_transport(tag)}")
    pmm = getattr(tag, "pmm", None)
    if isinstance(pmm, (bytes, bytearray)):
        lines.append(f"pmm: {pmm.hex().upper()}")
    lines.append("")

    if infer_transport(tag) != "felica":
        lines.append("result: skipped (non-FeliCa)")
        return "\n".join(lines) + "\n"

    systems, systems_error = request_system_codes(tag)
    lines.append("=== SYSTEM CODES ===")
    if systems_error:
        lines.append(f"error: {systems_error}")
    else:
        for system_code in systems:
            lines.append(f"0x{system_code:04X}")
    lines.append("")

    services_by_system = discover_services(tag)
    lines.append("=== SERVICES ===")
    for system_code, services in services_by_system.items():
        joined = ", ".join(f"0x{service:04X}" for service in services)
        lines.append(f"system 0x{system_code:04X}: {joined}")
    lines.append("")

    lines.append("=== PROBE TRANSIT ===")
    ok, detail = activate_system(tag, TRANSIT_SYSTEM_CODE)
    lines.append(f"activate 0x{TRANSIT_SYSTEM_CODE:04X}: {detail}")
    if ok:
        blocks, error = read_service_blocks(tag, BALANCE_SERVICE_CODE, 1)
        if error:
            lines.append(f"read 0x{BALANCE_SERVICE_CODE:04X}: {error}")
        elif blocks:
            lines.append(f"0x{BALANCE_SERVICE_CODE:04X}[0]: {format_block(blocks[0])}")
            balance = parse_transit_balance(blocks[0])
            lines.append(f"parsed_balance_yen: {balance}")

        blocks, error = read_service_blocks(tag, 0x090F, 3)
        if error:
            lines.append(f"read 0x090F: {error}")
        elif blocks:
            for index, block in enumerate(blocks):
                lines.append(f"0x090F[{index}]: {format_block(block)}")
    lines.append("")

    lines.append("=== PROBE STUDENT ===")
    found_student_service = False
    for system_code in STUDENT_SYSTEM_CANDIDATES:
        if STUDENT_ID_SERVICE_CODE in services_by_system.get(system_code, []):
            found_student_service = True
            ok, detail = activate_system(tag, system_code)
            lines.append(f"activate 0x{system_code:04X}: {detail}")
            if ok:
                blocks, error = read_service_blocks(tag, STUDENT_ID_SERVICE_CODE, 2)
                if error:
                    lines.append(f"read 0x{STUDENT_ID_SERVICE_CODE:04X}: {error}")
                elif blocks:
                    for index, block in enumerate(blocks):
                        lines.append(f"0x{STUDENT_ID_SERVICE_CODE:04X}[{index}]: {format_block(block)}")
                    lines.append(f"parsed_student_id: {extract_student_id(blocks)}")
    if not found_student_service:
        lines.append("student service not found")
    lines.append("")

    lines.append("=== FINAL JUDGEMENT ===")
    transit_services = services_by_system.get(TRANSIT_SYSTEM_CODE, [])
    if BALANCE_SERVICE_CODE in transit_services:
        if isinstance(pmm, (bytes, bytearray)) and pmm.hex().upper().startswith("0118"):
            lines.append("priority: mobile_suica")
        else:
            lines.append("priority: transit_card")
    elif any(STUDENT_ID_SERVICE_CODE in services for services in services_by_system.values()):
        lines.append("priority: student_card")
    else:
        lines.append("priority: unknown")

    return "\n".join(lines) + "\n"


def save_log(tag: nfc.tag.Tag, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = output_dir / f"{timestamp}_{get_tag_id(tag)}.txt"
    path.write_text(build_log(tag), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="captures_debug")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)

    try:
        with nfc.ContactlessFrontend("usb") as clf:
            print(f"Waiting for FeliCa tags. Debug output: {output_dir.resolve()}")
            felica_targets = (
                nfc.clf.RemoteTarget("212F"),
                nfc.clf.RemoteTarget("424F"),
            )

            while True:
                target = clf.sense(*felica_targets, iterations=5, interval=0.1)
                if target is None:
                    continue

                tag = nfc.tag.activate(clf, target)
                if tag is None or infer_transport(tag) != "felica":
                    continue

                path = save_log(tag, output_dir)
                print(f"saved: {path}")

                while tag.is_present:
                    time.sleep(0.1)
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(f"Failed to open NFC reader: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
