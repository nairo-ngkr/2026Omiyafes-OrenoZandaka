import argparse
import platform
import subprocess
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageOps


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = BASE_DIR / "Frame 1.png"
DEFAULT_SUMATRA = BASE_DIR / "SumatraPDF-3.6-64" / "SumatraPDF-3.6-64.exe"
DEFAULT_PRINTER = "Canon TS200 series"

OUTPUT_DIR = BASE_DIR / "output"
PDF_DIR = OUTPUT_DIR / "pdf"
PREPARED_DIR = OUTPUT_DIR / "prepared"
LOG_DIR = OUTPUT_DIR / "log"

DPI = 300
L_SIZE_SHORT_MM = 89
L_SIZE_LONG_MM = 127


def mm_to_px(mm: float) -> int:
    return round(mm / 25.4 * DPI)


def l_size_pixels(orientation: str) -> tuple[int, int]:
    if orientation == "landscape":
        return mm_to_px(L_SIZE_LONG_MM), mm_to_px(L_SIZE_SHORT_MM)

    return mm_to_px(L_SIZE_SHORT_MM), mm_to_px(L_SIZE_LONG_MM)


def l_size_print_settings(orientation: str, paper_name: str) -> str:
    return f"fit,paper={paper_name},{orientation}"


def resolve_orientation(image_path: Path, requested: str) -> str:
    if requested != "auto":
        return requested

    with Image.open(image_path) as image:
        image = ImageOps.exif_transpose(image)
        return "landscape" if image.width >= image.height else "portrait"


def prepare_l_size_image(input_path: Path, output_path: Path, orientation: str) -> None:
    target_size = l_size_pixels(orientation)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(input_path) as image:
        image = ImageOps.exif_transpose(image)

        if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
            background = Image.new("RGBA", image.size, "white")
            image = Image.alpha_composite(background, image.convert("RGBA"))

        image = image.convert("RGB")

        # L判フチなし前提なので、余白を作らず中央基準で塗り足しトリミングする。
        prepared = ImageOps.fit(
            image,
            target_size,
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )
        prepared.save(output_path, "PNG", dpi=(DPI, DPI))


def create_l_size_pdf(prepared_png_path: Path, pdf_path: Path) -> None:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(prepared_png_path) as image:
        image.convert("RGB").save(pdf_path, "PDF", resolution=float(DPI))


def print_pdf_with_sumatra(
    pdf_path: Path,
    sumatra_path: Path,
    printer_name: str,
    print_settings: str,
    show_dialog: bool,
) -> None:
    if platform.system() != "Windows":
        raise RuntimeError("実印刷は Windows 上で実行してください。Docker/Linux/macOS では PDF 生成までにしてください。")

    if not sumatra_path.exists():
        raise FileNotFoundError(f"SumatraPDF が見つかりません: {sumatra_path}")

    if show_dialog:
        command = [
            str(sumatra_path),
            "-print-dialog",
            "-print-settings",
            print_settings,
            str(pdf_path),
        ]
    else:
        command = [
            str(sumatra_path),
            "-print-to",
            printer_name,
            "-print-settings",
            print_settings,
            str(pdf_path),
        ]

    subprocess.run(command, check=True, cwd=sumatra_path.parent)


def write_log(
    input_path: Path,
    prepared_png_path: Path,
    pdf_path: Path,
    printer_name: str,
    orientation: str,
    print_settings: str,
    printed: bool,
) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = (
        f"{timestamp} | printed={printed} | printer={printer_name} | "
        f"paper=L | orientation={orientation} | dpi={DPI} | "
        f"settings={print_settings} | input={input_path} | "
        f"prepared={prepared_png_path} | pdf={pdf_path}"
    )
    with (LOG_DIR / "print_ts200_l_size.log").open("a", encoding="utf-8") as log:
        log.write(log_line + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Canon TS200 に L判フチなし想定の印刷ジョブを送ります。")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="印刷する画像。既定値は gen-print/Frame 1.png")
    parser.add_argument("--printer", default=DEFAULT_PRINTER, help="Windows のプリンター名")
    parser.add_argument("--sumatra", type=Path, default=DEFAULT_SUMATRA, help="SumatraPDF.exe のパス")
    parser.add_argument("--paper", default="L", help="Canon ドライバー上の L判用紙名。合わない場合は実機の表記に変更")
    parser.add_argument(
        "--orientation",
        choices=("portrait", "landscape", "auto"),
        default="portrait",
        help="印刷向き。Frame 1.png と同じ運用なら portrait",
    )
    parser.add_argument("--dialog", action="store_true", help="プリンターダイアログを出して確認してから印刷")
    parser.add_argument("--prepare-only", action="store_true", help="PDF 生成まで行い、プリンターへ送信しない")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = args.input.resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"入力画像が見つかりません: {input_path}")

    orientation = resolve_orientation(input_path, args.orientation)
    prepared_png_path = PREPARED_DIR / f"{input_path.stem}_l_size_{DPI}dpi_{orientation}.png"
    pdf_path = PDF_DIR / f"{input_path.stem}_l_size_{DPI}dpi_{orientation}.pdf"
    print_settings = l_size_print_settings(orientation, args.paper)

    prepare_l_size_image(input_path, prepared_png_path, orientation)
    create_l_size_pdf(prepared_png_path, pdf_path)

    printed = False
    if not args.prepare_only:
        print_pdf_with_sumatra(
            pdf_path=pdf_path,
            sumatra_path=args.sumatra.resolve(),
            printer_name=args.printer,
            print_settings=print_settings,
            show_dialog=args.dialog,
        )
        printed = True

    write_log(
        input_path=input_path,
        prepared_png_path=prepared_png_path,
        pdf_path=pdf_path,
        printer_name=args.printer,
        orientation=orientation,
        print_settings=print_settings,
        printed=printed,
    )

    print(f"prepared_png={prepared_png_path}")
    print(f"pdf={pdf_path}")
    print(f"printed={printed}")


if __name__ == "__main__":
    main()
