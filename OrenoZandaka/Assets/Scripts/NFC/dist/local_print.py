from __future__ import annotations

import sys
from pathlib import Path


def find_runtime_root() -> Path:
    """dist内から、run_local_print.py と gen-png/nfc_reader を持つ実行ルートを探す。"""
    current = Path(__file__).resolve().parent
    candidates = (
        current,
        current.parent,
    )

    for candidate in candidates:
        if (
            (candidate / "run_local_print.py").exists()
            and (candidate / "print_service.py").exists()
            and (candidate / "gen-png").is_dir()
            and (candidate / "nfc_reader").is_dir()
        ):
            return candidate

    searched = "\n".join(str(path) for path in candidates)
    raise FileNotFoundError(
        "実行に必要な run_local_print.py / print_service.py / gen-png / nfc_reader が見つかりません。\n"
        f"確認した場所:\n{searched}"
    )


def main() -> int:
    runtime_root = find_runtime_root()
    sys.path.insert(0, str(runtime_root))

    from run_local_print import main as run_main

    return run_main()


if __name__ == "__main__":
    raise SystemExit(main())
