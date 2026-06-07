import argparse
from datetime import datetime
from pathlib import Path
import re
from struct import pack, unpack
import sys
import time


import nfc.clf
import nfc.tag
from nfc.tag import TagCommandError
from nfc.tag.tt3 import BlockCode, ServiceCode
from nfc.tag.tt3_sony import activate as activate_sony_tag


SERVICE_LABELS = {
    0x008B: "Transit balance",
    0x010B: "Student ID",
    0x090F: "Transit history",
}

TRANSIT_SYSTEM_CODE = 0x0003
STUDENT_SYSTEM_CANDIDATES = (0x8277,)
MOBILE_SUICA_INFO_SERVICE = 0x188B
TYPE4A_AID_PROBES = (
    ("NDEF-v2", bytes.fromhex("D2760000850101")),
    ("NDEF-v1", bytes.fromhex("D2760000850100")),
    ("PPSE", b"2PAY.SYS.DDF01"),
    ("PSE", b"1PAY.SYS.DDF01"),
)


def sanitize_filename(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    return sanitized or "unknown_tag"


def get_tag_id(tag: nfc.tag.Tag) -> str:
    for attr in ("identifier", "_nfcid", "idm"):
        value = getattr(tag, attr, None)
        if isinstance(value, bytes) and value:
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


def try_read_service_blocks(
    tag: nfc.tag.Tag, service_code: int, block_count: int
) -> list[bytes] | None:
    if not hasattr(tag, "read_without_encryption"):
        return None

    service = make_service_code(service_code)
    blocks = [BlockCode(index, service=0) for index in range(block_count)]

    try:
        data = tag.read_without_encryption([service], blocks)
    except TagCommandError as exc:
        return [f"ERROR: {exc}".encode("ascii", errors="ignore")]
    except Exception as exc:
        return [f"ERROR: {exc}".encode("ascii", errors="ignore")]

    return [data[index:index + 16] for index in range(0, len(data), 16)]


def parse_transit_balance(block: bytes) -> int | None:
    if len(block) < 13:
        return None
    return int.from_bytes(block[11:13], byteorder="little")


def extract_ascii_student_id(blocks: list[bytes]) -> str | None:
    merged = b"".join(blocks)
    match = re.search(rb"[A-Z]{2}\d{5}", merged)
    if match:
        return match.group(0).decode("ascii")
    return None


def request_system_codes(tag: nfc.tag.Tag) -> list[int]:
    if hasattr(tag, "request_system_code"):
        return list(tag.request_system_code())

    if not hasattr(tag, "send_cmd_recv_rsp"):
        return []

    data = tag.send_cmd_recv_rsp(0x0C, b"", 0.002, check_status=False)
    if len(data) != 1 + data[0] * 2:
        return []
    return [unpack(">H", data[index:index + 2])[0] for index in range(1, len(data), 2)]


def activate_system(tag: nfc.tag.Tag, system_code: int) -> bool:
    if not hasattr(tag, "polling"):
        return False

    try:
        polled = tag.polling(system_code)
    except Exception:
        return False

    tag.idm, tag.pmm = polled[0], polled[1]
    if hasattr(tag, "sys"):
        tag.sys = system_code
    return True


def search_service_code(tag: nfc.tag.Tag, service_index: int) -> tuple[int, ...] | None:
    if hasattr(tag, "search_service_code"):
        return tag.search_service_code(service_index)

    if not hasattr(tag, "send_cmd_recv_rsp"):
        return None

    data = tag.send_cmd_recv_rsp(0x0A, pack("<H", service_index), 0.002, check_status=False)
    if data == b"\xFF\xFF":
        return None
    if len(data) == 2:
        return unpack("<H", data)
    if len(data) == 4:
        return unpack("<HH", data)
    return None


def discover_services(tag: nfc.tag.Tag) -> dict[int, list[int]]:
    services_by_system: dict[int, list[int]] = {}
    original_idm = getattr(tag, "idm", None)
    original_pmm = getattr(tag, "pmm", None)
    original_sys = getattr(tag, "sys", None)

    for system_code in request_system_codes(tag):
        if not activate_system(tag, system_code):
            continue

        services: list[int] = []
        for service_index in range(256):
            area_or_service = search_service_code(tag, service_index)
            if area_or_service is None:
                break
            if len(area_or_service) == 1:
                services.append(area_or_service[0])
        services_by_system[system_code] = services

    if original_idm is not None:
        tag.idm = original_idm
    if original_pmm is not None:
        tag.pmm = original_pmm
    if original_sys is not None and hasattr(tag, "sys"):
        tag.sys = original_sys

    return services_by_system


def infer_card_mode(services_by_system: dict[int, list[int]]) -> str:
    transit_services = services_by_system.get(TRANSIT_SYSTEM_CODE, [])
    if 0x008B in transit_services or 0x090F in transit_services:
        return "transit"

    for system_code in STUDENT_SYSTEM_CANDIDATES:
        if 0x010B in services_by_system.get(system_code, []):
            return "student"

    if any(0x010B in services for services in services_by_system.values()):
        return "student"

    return "unknown"


def infer_transport(tag: nfc.tag.Tag) -> str:
    module_name = tag.__class__.__module__
    if ".tt3" in module_name:
        return "felica"
    if ".tt4" in module_name:
        return "type4a"
    return "other"


def get_pmm_hex(tag: nfc.tag.Tag) -> str | None:
    pmm = getattr(tag, "pmm", None)
    if isinstance(pmm, (bytes, bytearray)) and pmm:
        return pmm.hex().upper()
    return None


def is_mobile_felica(tag: nfc.tag.Tag, services_by_system: dict[int, list[int]]) -> bool:
    pmm = get_pmm_hex(tag)
    if pmm and pmm.startswith("0118"):
        return True
    return MOBILE_SUICA_INFO_SERVICE in services_by_system.get(TRANSIT_SYSTEM_CODE, [])


def try_select_aid(tag: nfc.tag.Tag, aid: bytes) -> tuple[bool, str]:
    if not hasattr(tag, "send_apdu"):
        return False, "APDU not supported"

    try:
        response = tag.send_apdu(0x00, 0xA4, 0x04, 0x00, aid, mrl=256)
        return True, response.hex().upper() if response else "9000"
    except Exception as exc:
        return False, str(exc)


def read_type4a_summary(tag: nfc.tag.Tag) -> list[str]:
    lines = ["=== PRIORITY RESULT ===", "mode: mobile-or-type4a"]

    if getattr(tag, "ndef", None) and getattr(tag.ndef, "is_readable", False):
        lines.append("ndef: readable")
        lines.append(f"ndef_length: {getattr(tag.ndef, 'length', None)}")
    else:
        lines.append("ndef: unavailable")

    lines.append("apdu_probes:")
    for label, aid in TYPE4A_AID_PROBES:
        ok, detail = try_select_aid(tag, aid)
        status = "ok" if ok else "error"
        lines.append(f"  {label}: {status} ({detail})")

    lines.append("balance: unavailable via FeliCa service read on this transport")
    return lines


def read_transit_summary(tag: nfc.tag.Tag) -> list[str]:
    lines = ["=== PRIORITY RESULT ===", "mode: transit"]

    if not activate_system(tag, TRANSIT_SYSTEM_CODE):
        lines.append("balance: unavailable (failed to activate transit system)")
        return lines

    balance_blocks = try_read_service_blocks(tag, 0x008B, 1)
    if balance_blocks and not balance_blocks[0].startswith(b"ERROR: "):
        lines.append(f"balance_raw: {format_block(balance_blocks[0])}")
        balance = parse_transit_balance(balance_blocks[0])
        if balance is not None:
            lines.append(f"balance_yen: {balance}")
    elif balance_blocks:
        lines.append(
            "balance: unavailable "
            f"({balance_blocks[0].decode('ascii', errors='ignore')})"
        )
    else:
        lines.append("balance: unavailable")

    history_blocks = try_read_service_blocks(tag, 0x090F, 3)
    if history_blocks and not history_blocks[0].startswith(b"ERROR: "):
        for index, block in enumerate(history_blocks):
            lines.append(f"history[{index}]: {format_block(block)}")
    elif history_blocks:
        lines.append(
            "history: skipped "
            f"({history_blocks[0].decode('ascii', errors='ignore')})"
        )
    else:
        lines.append("history: skipped")

    return lines


def read_mobile_felica_summary(tag: nfc.tag.Tag, services_by_system: dict[int, list[int]]) -> list[str]:
    lines = read_transit_summary(tag)
    lines.insert(1, "variant: mobile-felica")
    lines.insert(2, "balance_source: service 0x008B bytes[11:13] little-endian")

    transit_services = services_by_system.get(TRANSIT_SYSTEM_CODE, [])
    if MOBILE_SUICA_INFO_SERVICE not in transit_services:
        return lines

    info_blocks = try_read_service_blocks(tag, MOBILE_SUICA_INFO_SERVICE, 2)
    if info_blocks and not info_blocks[0].startswith(b"ERROR: "):
        for index, block in enumerate(info_blocks):
            lines.append(f"mobile_info[{index}]: {format_block(block)}")
    elif info_blocks:
        lines.append(
            "mobile_info: unavailable "
            f"({info_blocks[0].decode('ascii', errors='ignore')})"
        )

    return lines


def read_student_summary(tag: nfc.tag.Tag, services_by_system: dict[int, list[int]]) -> list[str]:
    lines = ["=== PRIORITY RESULT ===", "mode: student"]

    target_system = None
    for system_code in STUDENT_SYSTEM_CANDIDATES:
        if 0x010B in services_by_system.get(system_code, []):
            target_system = system_code
            break
    if target_system is None:
        for system_code, services in services_by_system.items():
            if 0x010B in services:
                target_system = system_code
                break

    if target_system is None:
        lines.append("student_id: unavailable (service 0x010B not found)")
        return lines

    lines.append(f"student_system: 0x{target_system:04X}")
    if not activate_system(tag, target_system):
        lines.append("student_id: unavailable (failed to activate student system)")
        return lines

    student_blocks = try_read_service_blocks(tag, 0x010B, 2)
    if student_blocks and not student_blocks[0].startswith(b"ERROR: "):
        for index, block in enumerate(student_blocks):
            lines.append(f"student_raw[{index}]: {format_block(block)}")
        student_id = extract_ascii_student_id(student_blocks)
        if student_id:
            lines.append(f"student_id: {student_id}")
    elif student_blocks:
        lines.append(
            "student_id: unavailable "
            f"({student_blocks[0].decode('ascii', errors='ignore')})"
        )
    else:
        lines.append("student_id: unavailable")

    return lines


def build_report(tag: nfc.tag.Tag) -> tuple[str, str | None]:
    tag = normalize_tag(tag)

    lines: list[str] = []
    lines.append(f"captured_at: {datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"tag_type: {tag.__class__.__module__}.{tag.__class__.__name__}")
    lines.append(f"tag_repr: {tag}")

    identifier = get_tag_id(tag)
    lines.append(f"tag_id: {identifier}")
    lines.append(f"transport: {infer_transport(tag)}")
    lines.append("")
    lines.append("=== TAG DUMP ===")
    lines.extend(tag.dump())

    original_idm = getattr(tag, "idm", None)
    original_pmm = getattr(tag, "pmm", None)
    original_sys = getattr(tag, "sys", None)

    transport = infer_transport(tag)
    services_by_system = discover_services(tag) if transport == "felica" else {}
    if services_by_system:
        lines.append("")
        lines.append("=== SYSTEM / SERVICE DISCOVERY ===")
        for system_code, services in services_by_system.items():
            lines.append(f"System 0x{system_code:04X}")
            if services:
                lines.append(
                    "  services: " + ", ".join(f"0x{service:04X}" for service in services)
                )
            else:
                lines.append("  services: none found")

    card_mode = infer_card_mode(services_by_system) if transport == "felica" else "unknown"
    lines.append("")
    if transport == "type4a":
        lines.extend(read_type4a_summary(tag))
    elif transport != "felica":
        lines.append("=== PRIORITY RESULT ===")
        lines.append("mode: unsupported")
        lines.append(f"reason: {transport} tags do not expose FeliCa service codes")
    elif card_mode == "transit":
        if is_mobile_felica(tag, services_by_system):
            lines.extend(read_mobile_felica_summary(tag, services_by_system))
        else:
            lines.extend(read_transit_summary(tag))
    elif card_mode == "student":
        lines.extend(read_student_summary(tag, services_by_system))
    else:
        lines.append("=== PRIORITY RESULT ===")
        lines.append("mode: unknown")

    if original_idm is not None:
        tag.idm = original_idm
    if original_pmm is not None:
        tag.pmm = original_pmm
    if original_sys is not None and hasattr(tag, "sys"):
        tag.sys = original_sys

    lines.append("")
    lines.append("=== DIRECT SERVICE READS ===")
    for service_code, label in SERVICE_LABELS.items():
        if transport != "felica":
            lines.append(f"Service 0x{service_code:04X} ({label})")
            lines.append("  skipped: non-FeliCa tag")
            continue
        block_count = 20 if service_code == 0x090F else 8
        blocks = try_read_service_blocks(tag, service_code, block_count)
        lines.append(f"Service 0x{service_code:04X} ({label})")

        if not blocks:
            lines.append("  no data")
            continue

        if len(blocks) == 1 and blocks[0].startswith(b"ERROR: "):
            error_text = blocks[0].decode("ascii", errors="ignore")
            if service_code == 0x090F:
                lines.append(f"  skipped_or_unavailable: {error_text}")
            else:
                lines.append(f"  {error_text}")
            continue

        for index, block in enumerate(blocks):
            lines.append(f"  [{index:04X}] {format_block(block)}")

        if service_code == 0x008B and blocks:
            balance = parse_transit_balance(blocks[0])
            if balance is not None:
                lines.append(f"  parsed_balance_yen: {balance}")

        if service_code == 0x010B:
            student_id = extract_ascii_student_id(blocks)
            if student_id:
                lines.append(f"  parsed_student_id: {student_id}")

    ndef_text: str | None = None
    if getattr(tag, "ndef", None):
        lines.append("")
        lines.append("=== NDEF INFO ===")
        lines.append(f"is_readable: {getattr(tag.ndef, 'is_readable', None)}")
        lines.append(f"is_writeable: {getattr(tag.ndef, 'is_writeable', None)}")
        lines.append(f"capacity: {getattr(tag.ndef, 'capacity', None)}")
        lines.append(f"length: {getattr(tag.ndef, 'length', None)}")

        record_chunks: list[str] = []
        for index, record in enumerate(getattr(tag.ndef, "records", [])):
            lines.append("")
            lines.append(f"[record {index}]")
            lines.append(f"type: {getattr(record, 'type', '')}")
            lines.append(f"name: {getattr(record, 'name', '')}")
            lines.append(f"repr: {record}")

            payload = getattr(record, "data", None)
            if isinstance(payload, bytes):
                lines.append(f"payload_hex: {payload.hex()}")
                try:
                    decoded = payload.decode("utf-8")
                    lines.append("payload_utf8:")
                    lines.append(decoded)
                    record_chunks.append(decoded)
                except UnicodeDecodeError:
                    pass

        if record_chunks:
            ndef_text = "\n".join(record_chunks).strip() or None

    return "\n".join(lines) + "\n", ndef_text


def save_capture(tag: nfc.tag.Tag, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    tag_id = sanitize_filename(get_tag_id(tag))
    base_path = output_dir / f"{timestamp}_{tag_id}"

    report_text, ndef_text = build_report(tag)
    txt_path = base_path.with_suffix(".txt")
    txt_path.write_text(report_text, encoding="utf-8")

    if ndef_text:
        xml_path = base_path.with_suffix(".xml")
        xml_path.write_text(ndef_text, encoding="utf-8")

    return txt_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        default="captures",
        help="Directory where tag dumps will be saved.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)

    try:
        with nfc.ContactlessFrontend("usb") as clf:
            print(f"Waiting for NFC tags. Output directory: {output_dir.resolve()}")
            felica_targets = (
                nfc.clf.RemoteTarget("212F"),
                nfc.clf.RemoteTarget("424F"),
            )
            while True:
                target = clf.sense(*felica_targets, iterations=5, interval=0.1)
                if target is None:
                    continue

                tag = nfc.tag.activate(clf, target)
                if tag is None:
                    continue

                if infer_transport(tag) != "felica":
                    continue

                print("connected")
                saved_path = save_capture(tag, output_dir)
                print(f"saved: {saved_path}")

                while tag.is_present:
                    time.sleep(0.1)
    except KeyboardInterrupt:
        print("stopped")
        return 0
    except Exception as exc:
        print(f"Failed to open NFC reader: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
