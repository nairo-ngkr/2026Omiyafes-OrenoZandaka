from __future__ import annotations

import sys
import time
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from shinkan2026_nfc_counter_v1 import build_detection_event, build_release_event, run_forever
from transports import create_transport, load_transport_config


TRANSPORT = create_transport()
TRANSPORT_CONFIG = load_transport_config()


def handle_detected(value, idm) -> None:
    event = build_detection_event(value, idm)
    TRANSPORT.send(event)
    print(
        f"sent:{TRANSPORT_CONFIG.protocol}:{event['type']}:{event['value']}:{TRANSPORT_CONFIG.host}:{TRANSPORT_CONFIG.port}"
    )


def handle_released(idm) -> None:
    event = build_release_event(idm)
    TRANSPORT.send(event)
    print(
        f"sent:{TRANSPORT_CONFIG.protocol}:released:{idm}:{TRANSPORT_CONFIG.host}:{TRANSPORT_CONFIG.port}"
    )


def main() -> int:
    while True:
        try:
            run_forever(handle_detected, handle_released)
        except KeyboardInterrupt:
            return 0
        except OSError as exc:
            print(f"bridge connection error: {exc}", file=sys.stderr)
            time.sleep(2)
        except Exception as exc:
            print(f"bridge runtime error: {exc}", file=sys.stderr)
            time.sleep(2)


if __name__ == "__main__":
    raise SystemExit(main())
