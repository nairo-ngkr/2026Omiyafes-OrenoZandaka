from __future__ import annotations

import importlib.util
import json
import random
import sys
import threading
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Any

from print_ts200_l_size import (
    DEFAULT_PRINTER,
    DEFAULT_SUMATRA,
    l_size_print_settings,
    print_pdf_with_sumatra,
)


BASE_DIR = Path(__file__).resolve().parent
RENDERER_DIR = BASE_DIR / "gen-png"
RENDERER_MAIN = RENDERER_DIR / "main.py"
OUTPUT_DIR = BASE_DIR / "output" / "unity_pdf"
PREVIEW_DIR = BASE_DIR / "output" / "unity_png"
LOG_DIR = BASE_DIR / "output" / "log"
LOG_FILE = LOG_DIR / "printfromunity.log"
RANDOM_BALANCE_CONFIG_FILE = BASE_DIR / "random_balance_config.json"

SPECIAL_SHIBAZOU_BALANCES = {
    124,
    555,
    666,
    777,
    888,
    999,
    1111,
    2222,
    3333,
    4444,
    5555,
    6666,
    7777,
    8888,
    9999,
    11111,
}
PASSTHROUGH_KEYS = (
    "attribute",
    "skill",
    "skill_font_size",
    "phrase",
    "phrase_font_size",
    "habitat",
    "habitat_font_size",
    "description",
    "hp",
    "name",
    "skill_label",
    "phrase_label",
    "habitat_label",
    "background_image",
    "character_image",
)

_RENDERER_MODULE: ModuleType | None = None
_RENDERER_LOCK = threading.Lock()


class RequestError(ValueError):
    pass


@dataclass(frozen=True)
class PrintServiceConfig:
    output_dir: Path = OUTPUT_DIR
    preview_dir: Path | None = PREVIEW_DIR
    log_file: Path = LOG_FILE
    printer_name: str = DEFAULT_PRINTER
    sumatra_path: Path = DEFAULT_SUMATRA
    paper_name: str = "L"
    orientation: str = "portrait"
    show_dialog: bool = False
    prepare_only: bool = False
    allow_font_fallback: bool = False
    duplicate_guard: bool = True
    random_balance_uids: tuple[str, ...] = ("010101128F21C700",)
    random_balance_min: int = 0
    random_balance_max: int = 20000
    random_balance_cooldown_seconds: int = 50
    random_balance_config_file: Path | None = RANDOM_BALANCE_CONFIG_FILE


@dataclass(frozen=True)
class PrintResult:
    ok: bool
    duplicate: bool
    printed: bool
    uid: str
    balance: str
    balance_int: int | None
    template: str | None
    payload: dict[str, Any]
    pdf: str
    previews: list[str]
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def first_value(params: dict[str, list[str]], key: str, default: str = "") -> str:
    values = params.get(key)
    if not values:
        return default
    return values[0]


def flatten_query(params: dict[str, list[str]]) -> dict[str, str | list[str]]:
    query: dict[str, str | list[str]] = {}
    for key, values in params.items():
        query[key] = values[0] if len(values) == 1 else values
    return query


def normalize_params(params: dict[str, Any] | None) -> dict[str, list[str]]:
    normalized: dict[str, list[str]] = {}
    if not params:
        return normalized
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, list):
            normalized[key] = [str(item) for item in value]
        else:
            normalized[key] = [str(value)]
    return normalized


def parse_balance(balance_raw: str) -> int | None:
    try:
        return int(balance_raw)
    except ValueError:
        return None


def normalize_uid(uid: str) -> str:
    return "".join(char for char in str(uid).upper() if char in "0123456789ABCDEF")


def load_random_balance_settings(config: PrintServiceConfig) -> tuple[tuple[str, ...], int, int, int]:
    uids = config.random_balance_uids
    min_balance = config.random_balance_min
    max_balance = config.random_balance_max
    cooldown_seconds = config.random_balance_cooldown_seconds

    if config.random_balance_config_file is None or not config.random_balance_config_file.exists():
        return uids, min_balance, max_balance, cooldown_seconds

    try:
        raw = json.loads(config.random_balance_config_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return uids, min_balance, max_balance, cooldown_seconds

    if raw.get("enabled") is False:
        return (), min_balance, max_balance, cooldown_seconds

    raw_uids = raw.get("uids", uids)
    if isinstance(raw_uids, str):
        uids = tuple(uid.strip() for uid in raw_uids.split(",") if uid.strip())
    elif isinstance(raw_uids, list):
        uids = tuple(str(uid).strip() for uid in raw_uids if str(uid).strip())

    try:
        min_balance = int(raw.get("min", min_balance))
        max_balance = int(raw.get("max", max_balance))
        cooldown_seconds = int(raw.get("cooldown_seconds", cooldown_seconds))
    except (TypeError, ValueError):
        min_balance = config.random_balance_min
        max_balance = config.random_balance_max
        cooldown_seconds = config.random_balance_cooldown_seconds

    return uids, min_balance, max_balance, max(0, cooldown_seconds)


def is_random_balance_uid(uid: str, random_balance_uids: tuple[str, ...]) -> bool:
    target_uid = normalize_uid(uid)
    return bool(target_uid) and any(target_uid == normalize_uid(config_uid) for config_uid in random_balance_uids)


def random_balance(min_balance: int, max_balance: int) -> int:
    lower = min(min_balance, max_balance)
    upper = max(min_balance, max_balance)
    ransuu = random.random()
    if ransuu < 0.12:
        random_balance_a = random.randint(0, 299)
    elif ransuu < 0.24:
        random_balance_a = random.randint(300, 899)
    elif ransuu < 0.36:
        random_balance_a = random.randint(900, 1499)
    elif ransuu < 0.48:
        random_balance_a = random.randint(1500, 2999)
    elif ransuu < 0.60: 
        random_balance_a = random.randint(3000, 4999)
    elif ransuu < 0.72:
        random_balance_a = random.randint(5000, 9999)
    elif ransuu < 0.84:
        random_balance_a = random.randint(10000, 20000)
    elif ransuu < 0.96:
        random_balance_a = random.randint(0, 5000)
    else:        
        random_balance_a = [124, 555, 666, 777, 888, 999, 1111, 2222, 3333, 4444, 5555, 6666, 7777, 8888, 9999, 11111][random.randint(0, 15)]

    return random_balance_a

def last_random_balance_printed_at(uid: str, log_file: Path = LOG_FILE) -> datetime | None:
    if not log_file.exists():
        return None

    target_uid = normalize_uid(uid)
    latest: datetime | None = None
    with log_file.open("r", encoding="utf-8") as log:
        for line in log:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            if normalize_uid(record.get("uid", "")) != target_uid or record.get("printed") is not True:
                continue

            query = record.get("query", {})
            if not isinstance(query, dict) or str(query.get("random_balance_override", "")).lower() != "true":
                continue

            timestamp = record.get("timestamp")
            if not isinstance(timestamp, str):
                continue

            try:
                printed_at = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue

            if latest is None or printed_at > latest:
                latest = printed_at

    return latest


def is_random_balance_cooldown_active(uid: str, cooldown_seconds: int, log_file: Path = LOG_FILE) -> bool:
    if cooldown_seconds <= 0:
        return False

    printed_at = last_random_balance_printed_at(uid, log_file)
    if printed_at is None:
        return False

    return (datetime.now() - printed_at).total_seconds() < cooldown_seconds


def select_template(balance_int: int | None) -> str:
    if balance_int in SPECIAL_SHIBAZOU_BALANCES:
        return "shibazou"
    if balance_int is None or balance_int < 0 or balance_int > 20000:
        return "gonta"
    if balance_int <= 299:
        return "slime"
    if balance_int <= 899:
        return "mojaokun"
    if balance_int <= 1499:
        return "peka_pika"
    if balance_int <= 2999:
        return "patasan"
    if balance_int <= 4999:
        return "nurunurun"
    if balance_int <= 9999:
        return "kukuros"
    return "gonta"


def build_pdf_payload(uid: str, balance_raw: str, params: dict[str, list[str]] | None = None) -> dict[str, Any]:
    """UID/残高/追加クエリをカード生成 payload に変換する。"""
    if not uid:
        raise RequestError("`uid` を指定してください。")
    if not balance_raw:
        raise RequestError("`balance` を指定してください。")

    params = params or {}
    balance_int = parse_balance(balance_raw)
    payload: dict[str, Any] = {
        "template": select_template(balance_int),
        "hp": balance_raw,
    }

    for key in PASSTHROUGH_KEYS:
        value = first_value(params, key)
        if value:
            payload[key] = value

    return payload


def has_printed_duplicate(uid: str, balance_raw: str, log_file: Path = LOG_FILE) -> bool:
    if not log_file.exists():
        return False
    with log_file.open("r", encoding="utf-8") as log:
        for line in log:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("uid") == uid and record.get("balance_raw") == balance_raw and record.get("printed") is True:
                return True
    return False


def write_log(record: dict[str, Any], log_file: Path = LOG_FILE) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as log:
        log.write(json.dumps(record, ensure_ascii=False) + "\n")


def build_log_record(
    uid: str,
    balance_raw: str,
    balance_int: int | None,
    template: str | None,
    duplicate: bool,
    printed: bool,
    pdf_path: Path | None,
    previews: list[Path],
    query: dict[str, str | list[str]],
    payload: dict[str, Any],
    error: str | None = None,
) -> dict[str, Any]:
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "uid": uid,
        "balance_raw": balance_raw,
        "balance_int": balance_int,
        "template": template,
        "duplicate": duplicate,
        "printed": printed,
        "pdf": str(pdf_path) if pdf_path is not None else "",
        "previews": [str(path) for path in previews],
        "query": query,
        "payload": payload,
        "error": error,
    }


def _load_renderer() -> ModuleType:
    global _RENDERER_MODULE
    with _RENDERER_LOCK:
        if _RENDERER_MODULE is not None:
            return _RENDERER_MODULE
        spec = importlib.util.spec_from_file_location("gen_png_renderer", RENDERER_MAIN)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"renderer を読み込めません: {RENDERER_MAIN}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        _RENDERER_MODULE = module
        return module


def render_payload_to_files(
    payload: dict[str, Any],
    output_dir: Path,
    preview_dir: Path | None,
    allow_font_fallback: bool,
) -> tuple[Path, list[Path]]:
    renderer = _load_renderer()
    cards = renderer.parse_cards_payload(payload)
    fonts = renderer.load_fonts(allow_font_fallback)
    images = [renderer.render_card(card, RENDERER_DIR, fonts) for card in cards]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / f"unity_{timestamp}.pdf"
    renderer.save_outputs(images, pdf_path, None)

    preview_paths: list[Path] = []
    if preview_dir is not None:
        preview_run_dir = preview_dir / f"unity_{timestamp}"
        preview_run_dir.mkdir(parents=True, exist_ok=True)
        for index, image in enumerate(images, 1):
            preview_path = preview_run_dir / f"card_{index:03}.png"
            image.save(preview_path, "PNG", dpi=(renderer.DPI, renderer.DPI))
            preview_paths.append(preview_path)

    return pdf_path, preview_paths


def process_print_request(
    uid: str,
    balance_raw: str | int,
    params: dict[str, Any] | None = None,
    config: PrintServiceConfig | None = None,
) -> PrintResult:
    current = config or PrintServiceConfig()
    normalized_params = normalize_params(params)
    original_balance_text = str(balance_raw)
    random_balance_uids, random_balance_min, random_balance_max, random_balance_cooldown_seconds = load_random_balance_settings(current)
    random_override = is_random_balance_uid(uid, random_balance_uids)
    balance_text = str(random_balance(random_balance_min, random_balance_max)) if random_override else original_balance_text
    if random_override:
        normalized_params.setdefault("original_balance", [original_balance_text])
        normalized_params.setdefault("random_balance_override", ["true"])

    query = flatten_query({"uid": [uid], "balance": [balance_text], **normalized_params})
    payload: dict[str, Any] = {}
    pdf_path: Path | None = None
    preview_paths: list[Path] = []
    printed = False
    balance_int = parse_balance(balance_text) if balance_text else None
    template = select_template(balance_int) if balance_text else None

    try:
        payload = build_pdf_payload(uid, balance_text, normalized_params)
        template = payload.get("template")

        if random_override and is_random_balance_cooldown_active(uid, random_balance_cooldown_seconds, current.log_file):
            record = build_log_record(
                uid,
                balance_text,
                balance_int,
                template,
                True,
                False,
                None,
                [],
                query,
                payload,
                f"random balance cooldown active ({random_balance_cooldown_seconds}s)",
            )
            write_log(record, current.log_file)
            return PrintResult(True, True, False, uid, balance_text, balance_int, template, payload, "", [])

        if current.duplicate_guard and not random_override and has_printed_duplicate(uid, balance_text, current.log_file):
            record = build_log_record(
                uid,
                balance_text,
                balance_int,
                template,
                True,
                False,
                None,
                [],
                query,
                payload,
            )
            write_log(record, current.log_file)
            return PrintResult(True, True, False, uid, balance_text, balance_int, template, payload, "", [])

        pdf_path, preview_paths = render_payload_to_files(
            payload,
            current.output_dir.resolve(),
            current.preview_dir.resolve() if current.preview_dir else None,
            current.allow_font_fallback,
        )

        if not current.prepare_only:
            print_pdf_with_sumatra(
                pdf_path=pdf_path,
                sumatra_path=current.sumatra_path.resolve(),
                printer_name=current.printer_name,
                print_settings=l_size_print_settings(current.orientation, current.paper_name),
                show_dialog=current.show_dialog,
            )
            printed = True

        record = build_log_record(
            uid,
            balance_text,
            balance_int,
            template,
            False,
            printed,
            pdf_path,
            preview_paths,
            query,
            payload,
        )
        write_log(record, current.log_file)
        return PrintResult(
            True,
            False,
            printed,
            uid,
            balance_text,
            balance_int,
            template,
            payload,
            str(pdf_path),
            [str(path) for path in preview_paths],
        )
    except Exception as exc:
        record = build_log_record(
            uid,
            balance_text,
            balance_int,
            template,
            False,
            printed,
            pdf_path,
            preview_paths,
            query,
            payload,
            str(exc),
        )
        write_log(record, current.log_file)
        if isinstance(exc, RequestError):
            raise
        raise
