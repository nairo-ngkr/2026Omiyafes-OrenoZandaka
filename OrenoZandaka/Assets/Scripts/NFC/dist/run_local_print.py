from __future__ import annotations

import argparse
import importlib.util
import json
import socket
import sys
import threading
import time
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from print_service import (
    OUTPUT_DIR,
    PREVIEW_DIR,
    PrintServiceConfig,
    RequestError,
    process_print_request,
)
from print_ts200_l_size import DEFAULT_PRINTER, DEFAULT_SUMATRA


BASE_DIR = Path(__file__).resolve().parent
NFC_DIR = BASE_DIR / "nfc_reader"
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8080
DEFAULT_UNITY_HOST = "127.0.0.1"
DEFAULT_UNITY_PORT = 9000
DEFAULT_RANDOM_BALANCE_UIDS = "010101128F21C700"


def parse_uid_list(value: str) -> tuple[str, ...]:
    return tuple(uid.strip() for uid in value.split(",") if uid.strip())


class UnityTcpNotifier:
    def __init__(self, host: str, port: int, timeout_seconds: float, enabled: bool = True) -> None:
        self.host = host
        self.port = port
        self.timeout_seconds = timeout_seconds
        self.enabled = enabled

    def send(self, event: dict[str, Any]) -> None:
        event.setdefault("sent_at", datetime.now(timezone.utc).isoformat())
        if not self.enabled:
            print(f"unity_event_disabled={json.dumps(event, ensure_ascii=False)}")
            return

        payload = (json.dumps(event, ensure_ascii=False) + "\n").encode("utf-8")
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout_seconds) as sock:
                sock.sendall(payload)
        except OSError as exc:
            print(f"unity_event_error host={self.host} port={self.port} error={exc}", file=sys.stderr)


def print_result_event(event: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "event": event,
        "uid": result.get("uid"),
        "balance": result.get("balance"),
        "balance_int": result.get("balance_int"),
        "template": result.get("template"),
        "printed": result.get("printed"),
        "duplicate": result.get("duplicate"),
        "pdf": result.get("pdf"),
        "previews": result.get("previews", []),
        "error": result.get("error"),
    }


def json_response(handler: BaseHTTPRequestHandler, status: HTTPStatus, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class LocalPrintHandler(BaseHTTPRequestHandler):
    server_version = "LocalNfcPrintHTTP/1.0"

    def do_GET(self) -> None:
        if self.path.split("?", 1)[0] != "/health":
            json_response(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": "path は /health を使ってください。"})
            return
        json_response(
            self,
            HTTPStatus.OK,
            {
                "ok": True,
                "service": "local-nfc-print",
                "unity_host": self.server.notifier.host,
                "unity_port": self.server.notifier.port,
                "prepare_only": self.server.print_config.prepare_only,
            },
        )

    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0]
        if path not in ("/print", "/nfc/mock"):
            json_response(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": "path は /print または /nfc/mock を使ってください。"})
            return

        try:
            payload = self._read_json()
            uid = str(payload.get("uid") or payload.get("idm") or "")
            balance = payload.get("balance", payload.get("value", ""))
            extras = {key: value for key, value in payload.items() if key not in {"uid", "idm", "balance", "value"}}

            self.server.notifier.send({"event": "detected", "uid": uid, "balance": balance, "source": path.lstrip("/")})
            with self.server.request_lock:
                self.server.notifier.send({"event": "printing", "uid": uid, "balance": balance, "source": path.lstrip("/")})
                result = process_print_request(uid, balance, extras, self.server.print_config)
            result_dict = result.to_dict()
            self.server.notifier.send(print_result_event("duplicate" if result.duplicate else "printed", result_dict))
            json_response(self, HTTPStatus.OK, result_dict)
        except RequestError as exc:
            self.server.notifier.send({"event": "error", "error": str(exc), "source": path.lstrip("/")})
            json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self.server.notifier.send({"event": "error", "error": str(exc), "source": path.lstrip("/")})
            json_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(exc)})

    def _read_json(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            raise RequestError("JSONボディを送信してください。")
        raw = self.rfile.read(content_length).decode("utf-8")
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise RequestError("JSONオブジェクトを送信してください。")
        return payload

    def log_message(self, format: str, *args: Any) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{timestamp} | {self.address_string()} | {format % args}")


class LocalPrintServer(ThreadingHTTPServer):
    print_config: PrintServiceConfig
    notifier: UnityTcpNotifier
    request_lock: threading.Lock


def start_http_server(
    host: str,
    port: int,
    print_config: PrintServiceConfig,
    notifier: UnityTcpNotifier,
) -> LocalPrintServer:
    server = LocalPrintServer((host, port), LocalPrintHandler)
    server.print_config = print_config
    server.notifier = notifier
    server.request_lock = threading.Lock()
    thread = threading.Thread(target=server.serve_forever, name="local-print-http", daemon=True)
    thread.start()
    return server


def handle_nfc_event(value: Any, idm: str, print_config: PrintServiceConfig, notifier: UnityTcpNotifier) -> None:
    uid = idm
    balance = value
    try:
        result = process_print_request(uid, balance, config=print_config)
        result_dict = result.to_dict()
        effective_balance = result.balance_int if result.balance_int is not None else balance
        notifier.send({
            "event": "detected",
            "type": "transit",
            "value": effective_balance,
            "uid": uid,
            "balance": effective_balance,
            "idm": idm,
        })
        print(json.dumps(result_dict, ensure_ascii=False))
    except Exception as exc:
        notifier.send({"event": "error", "uid": uid, "balance": balance, "error": str(exc)})
        print(f"nfc_print_error uid={uid} balance={balance} error={exc}", file=sys.stderr)


def run_nfc_loop(print_config: PrintServiceConfig, notifier: UnityTcpNotifier) -> None:
    nfc_script = NFC_DIR / "shinkan2026_nfc_counter_v1.py"
    local_paths = {str(BASE_DIR), str(NFC_DIR)}
    original_sys_path = list(sys.path)
    local_nfc_module = sys.modules.get("nfc")

    if local_nfc_module is not None:
        module_file = getattr(local_nfc_module, "__file__", "")
        try:
            is_local_nfc = Path(module_file).resolve().is_relative_to(NFC_DIR)
        except (OSError, ValueError):
            is_local_nfc = False
        if is_local_nfc:
            for module_name in list(sys.modules):
                if module_name == "nfc" or module_name.startswith("nfc."):
                    del sys.modules[module_name]

    try:
        sys.path = [path for path in sys.path if path not in local_paths]
        spec = importlib.util.spec_from_file_location("shinkan2026_nfc_counter_v1", nfc_script)
        if spec is None or spec.loader is None:
            raise ImportError(f"NFCスクリプトを読み込めません: {nfc_script}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        run_forever = module.run_forever
    finally:
        sys.path = original_sys_path

    while True:
        try:
            run_forever(
                lambda value, idm: handle_nfc_event(value, idm, print_config, notifier),
                lambda idm: notifier.send({"event": "released", "idm": idm}),
            )
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            print(f"nfc_loop_error error={exc}", file=sys.stderr)
            time.sleep(2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="NFC検出からUnity通知、カード生成、TS200印刷までをローカルで実行します。")
    parser.add_argument("--host", default=DEFAULT_HOST, help="手動テスト用HTTP APIの待ち受けホスト")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="手動テスト用HTTP APIの待ち受けポート")
    parser.add_argument("--unity-host", default=DEFAULT_UNITY_HOST, help="Unity TCP listener のホスト/IP")
    parser.add_argument("--unity-port", type=int, default=DEFAULT_UNITY_PORT, help="Unity TCP listener のポート")
    parser.add_argument("--unity-timeout", type=float, default=3.0, help="Unity TCP接続タイムアウト秒")
    parser.add_argument("--no-unity", action="store_true", help="UnityへTCP通知せず、標準出力にイベントを表示")
    parser.add_argument("--no-nfc", action="store_true", help="NFCループを起動せず、HTTP APIだけ起動")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="生成PDFの保存先")
    parser.add_argument("--preview-dir", type=Path, default=PREVIEW_DIR, help="確認用PNGの保存先")
    parser.add_argument("--printer", default=DEFAULT_PRINTER, help="Windows のプリンター名")
    parser.add_argument("--sumatra", type=Path, default=DEFAULT_SUMATRA, help="SumatraPDF.exe のパス")
    parser.add_argument("--paper", default="L", help="Canon ドライバー上の L判用紙名")
    parser.add_argument("--orientation", choices=("portrait", "landscape"), default="portrait", help="印刷向き")
    parser.add_argument("--dialog", action="store_true", help="プリンターダイアログを出して確認してから印刷")
    parser.add_argument("--prepare-only", action="store_true", help="PDF/PNG生成まで行い、プリンターへ送信しない")
    parser.add_argument("--allow-font-fallback", action="store_true", help="x10フォントが無い場合にx8で代替します。")
    parser.add_argument(
        "--random-balance-uids",
        default=DEFAULT_RANDOM_BALANCE_UIDS,
        help="Comma-separated UIDs whose balance is replaced with a random value and duplicate guard is skipped.",
    )
    parser.add_argument("--random-balance-min", type=int, default=0, help="Minimum random balance for random-balance UIDs.")
    parser.add_argument("--random-balance-max", type=int, default=20000, help="Maximum random balance for random-balance UIDs.")
    parser.add_argument("--random-balance-cooldown-seconds", type=int, default=50, help="Cooldown seconds per random-balance UID.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print_config = PrintServiceConfig(
        output_dir=args.output_dir.resolve(),
        preview_dir=args.preview_dir.resolve() if args.preview_dir else None,
        printer_name=args.printer,
        sumatra_path=args.sumatra.resolve(),
        paper_name=args.paper,
        orientation=args.orientation,
        show_dialog=args.dialog,
        prepare_only=args.prepare_only,
        allow_font_fallback=args.allow_font_fallback,
        random_balance_uids=parse_uid_list(args.random_balance_uids),
        random_balance_min=args.random_balance_min,
        random_balance_max=args.random_balance_max,
        random_balance_cooldown_seconds=args.random_balance_cooldown_seconds,
    )
    notifier = UnityTcpNotifier(args.unity_host, args.unity_port, args.unity_timeout, enabled=not args.no_unity)
    server = start_http_server(args.host, args.port, print_config, notifier)

    print(f"http_api=http://{args.host}:{args.port}")
    print(f"unity_tcp={args.unity_host}:{args.unity_port} enabled={not args.no_unity}")
    print(f"output_dir={print_config.output_dir}")
    print(f"preview_dir={print_config.preview_dir}")
    print(f"prepare_only={print_config.prepare_only}")
    print(f"random_balance_uids={','.join(print_config.random_balance_uids)}")
    print(f"random_balance_cooldown_seconds={print_config.random_balance_cooldown_seconds}")

    try:
        if args.no_nfc:
            print("no_nfc=True のため HTTP API のみ待ち受けます。Ctrl+C で停止します。")
            while True:
                time.sleep(3600)
        else:
            run_nfc_loop(print_config, notifier)
    except KeyboardInterrupt:
        print("\n停止しました。")
        return 0
    finally:
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
