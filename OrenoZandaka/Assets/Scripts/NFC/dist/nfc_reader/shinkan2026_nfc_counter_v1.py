import json
import sys
import time
from datetime import datetime, timezone

import nfc.clf
import nfc.tag
from nfc.tag.tt3 import BlockCode, ServiceCode
from nfc.tag.tt3_sony import activate as activate_sony_tag


TRANSIT_SYSTEM_CODE = 0x0003
BALANCE_SERVICE_CODE = 0x008B


def build_detection_event(value, idm) -> dict[str, str | int | None]:
    return {
        "type": "transit",
        "value": value,
        "idm": idm,
        "detected_at": datetime.now(timezone.utc).isoformat(),
    }


def build_release_event(idm) -> dict[str, str | None]:
    return {
        "event": "released",
        "idm": idm,
        "released_at": datetime.now(timezone.utc).isoformat(),
    }

def process_detected_value(value, idm) -> None:
    print("残高 : " + str(value) + "円,  idm : " + str(idm))


def infer_transport(tag: nfc.tag.Tag) -> str:
    module_name = tag.__class__.__module__
    if ".tt3" in module_name:
        return "felica"
    if ".tt4" in module_name:
        return "type4a"
    return "other"


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


def activate_system(tag: nfc.tag.Tag, system_code: int) -> bool:
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


def read_service_blocks(tag: nfc.tag.Tag, service_code: int, block_count: int) -> list[bytes] | None:
    if not hasattr(tag, "read_without_encryption"):
        return None

    service = make_service_code(service_code)
    blocks = [BlockCode(index, service=0) for index in range(block_count)]

    try:
        data = tag.read_without_encryption([service], blocks)
    except Exception:
        return None

    return [data[index:index + 16] for index in range(0, len(data), 16)]


def parse_transit_balance(block: bytes) -> int | None:
    if len(block) < 13:
        return None
    return int.from_bytes(block[11:13], byteorder="little")


def get_idm_hex(tag: nfc.tag.Tag) -> str:
    idm = getattr(tag, "idm", b"")
    if isinstance(idm, (bytes, bytearray)) and idm:
        return idm.hex().upper()
    return "UNKNOWN"


def read_transit(tag: nfc.tag.Tag) -> tuple[int, str] | None:
    if not activate_system(tag, TRANSIT_SYSTEM_CODE):
        return None

    blocks = read_service_blocks(tag, BALANCE_SERVICE_CODE, 1)
    if not blocks:
        return None

    balance = parse_transit_balance(blocks[0])
    if balance is None:
        return None

    return balance, get_idm_hex(tag)


def run_forever(on_detect, on_release=None) -> None:
    print("Waiting for FeliCa events for shinkan2026...")
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
            if tag is None or infer_transport(tag) != "felica":
                continue

            tag = normalize_tag(tag)

            transit = read_transit(tag)
            if transit is not None:
                balance, idm = transit
                on_detect(balance, idm)

                while tag.is_present:
                    time.sleep(0.1)

                if on_release is not None:
                    on_release(idm)
            else:
                while tag.is_present:
                    time.sleep(0.1)


def main() -> int:
    try:
        run_forever(process_detected_value)
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(f"Application error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


