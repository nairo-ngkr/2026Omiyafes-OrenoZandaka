import re
import sys
import time

import nfc.clf
import nfc.tag
from nfc.tag.tt3 import BlockCode, ServiceCode
from nfc.tag.tt3_sony import activate as activate_sony_tag


TRANSIT_SYSTEM_CODE = 0x0003
STUDENT_SYSTEM_CANDIDATES = (0x8277,)
BALANCE_SERVICE_CODE = 0x008B
STUDENT_ID_SERVICE_CODE = 0x010B


def _infer_transport(tag: nfc.tag.Tag) -> str:
    module_name = tag.__class__.__module__
    if ".tt3" in module_name:
        return "felica"
    if ".tt4" in module_name:
        return "type4a"
    return "other"


def _normalize_tag(tag: nfc.tag.Tag) -> nfc.tag.Tag:
    if _infer_transport(tag) != "felica":
        return tag

    try:
        sony_tag = activate_sony_tag(tag.clf, tag.target)
    except Exception:
        return tag

    return sony_tag or tag


def _make_service_code(service_code: int) -> ServiceCode:
    return ServiceCode(service_code >> 6, service_code & 0x3F)


def _activate_system(tag: nfc.tag.Tag, system_code: int) -> bool:
    if not hasattr(tag, "polling"):
        return False

    try:
        idm, pmm = tag.polling(system_code)[:2]
    except Exception:
        return False

    tag.idm = idm
    tag.pmm = pmm
    if hasattr(tag, "sys"):
        tag.sys = system_code
    return True


def _request_system_codes(tag: nfc.tag.Tag) -> list[int]:
    if hasattr(tag, "request_system_code"):
        try:
            return list(tag.request_system_code())
        except Exception:
            return []
    return []


def _read_service_blocks(tag: nfc.tag.Tag, service_code: int, block_count: int) -> list[bytes] | None:
    if not hasattr(tag, "read_without_encryption"):
        return None

    service = _make_service_code(service_code)
    blocks = [BlockCode(index, service=0) for index in range(block_count)]

    try:
        data = tag.read_without_encryption([service], blocks)
    except Exception:
        return None

    return [data[index:index + 16] for index in range(0, len(data), 16)]


def _parse_transit_balance(block: bytes) -> int | None:
    if len(block) < 13:
        return None
    return int.from_bytes(block[11:13], byteorder="little")


def _extract_student_id(blocks: list[bytes]) -> str | None:
    match = re.search(rb"[A-Z]{2}\d{5}", b"".join(blocks))
    if match:
        return match.group(0).decode("ascii")
    return None


def _get_idm_hex(tag: nfc.tag.Tag) -> str:
    idm = getattr(tag, "idm", b"")
    if isinstance(idm, (bytes, bytearray)) and idm:
        return idm.hex().upper()
    return "UNKNOWN"


def _is_mobile_felica(tag: nfc.tag.Tag) -> bool:
    pmm = getattr(tag, "pmm", b"")
    if isinstance(pmm, (bytes, bytearray)) and pmm.hex().upper().startswith("0118"):
        return True
    return False


def _read_transit(tag: nfc.tag.Tag) -> dict | None:
    if not _activate_system(tag, TRANSIT_SYSTEM_CODE):
        return None

    blocks = _read_service_blocks(tag, BALANCE_SERVICE_CODE, 1)
    if not blocks:
        return None

    balance = _parse_transit_balance(blocks[0])
    if balance is None:
        return None

    kind = "mobile_suica_balance" if _is_mobile_felica(tag) else "transit_balance"
    return {
        "kind": kind,
        "balance": balance,
        "idm": _get_idm_hex(tag),
    }


def _read_student(tag: nfc.tag.Tag) -> dict | None:
    for system_code in STUDENT_SYSTEM_CANDIDATES:
        if not _activate_system(tag, system_code):
            continue

        blocks = _read_service_blocks(tag, STUDENT_ID_SERVICE_CODE, 2)
        if not blocks:
            continue

        student_id = _extract_student_id(blocks)
        if student_id is not None:
            return {
                "kind": "student_id",
                "student_id": student_id,
            }

    for system_code in _request_system_codes(tag):
        if not _activate_system(tag, system_code):
            continue

        blocks = _read_service_blocks(tag, STUDENT_ID_SERVICE_CODE, 2)
        if not blocks:
            continue

        student_id = _extract_student_id(blocks)
        if student_id is not None:
            return {
                "kind": "student_id",
                "student_id": student_id,
            }

    return None


def read_one_felica_event() -> dict | None:
    with nfc.ContactlessFrontend("usb") as clf:
        felica_targets = (
            nfc.clf.RemoteTarget("212F"),
            nfc.clf.RemoteTarget("424F"),
        )

        while True:
            target = clf.sense(*felica_targets, iterations=5, interval=0.1)
            if target is None:
                continue

            tag = nfc.tag.activate(clf, target)
            if tag is None or _infer_transport(tag) != "felica":
                continue

            tag = _normalize_tag(tag)

            result = _read_transit(tag)
            if result is None:
                result = _read_student(tag)

            while tag.is_present:
                time.sleep(0.1)

            return result


def run_forever(on_detect) -> None:
    print("Waiting for FeliCa tags...")
    while True:
        result = read_one_felica_event()
        if result is None:
            continue

        if result["kind"] == "student_id":
            on_detect(result["student_id"], None)
        else:
            on_detect(result["balance"], result["idm"])


def main() -> int:
    try:
        def print_detected(value, idm) -> None:
            if idm is None:
                print(f"student_id:{value}")
            else:
                print(f"value:{value},idm={idm}")

        run_forever(print_detected)
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(f"Failed to open NFC reader: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
