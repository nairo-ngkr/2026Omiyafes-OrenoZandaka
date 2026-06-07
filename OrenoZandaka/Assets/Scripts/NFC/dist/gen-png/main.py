# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
DEFAULT_INPUT = BASE_DIR / "examples" / "card.json"
DEFAULT_OUTPUT = BASE_DIR / "output" / "card.pdf"
CANVAS_SIZE = (1051, 1500)
FIGMA_CANVAS_SIZE = (1051, 1501)
DPI = 300
FONT_DIR = BASE_DIR / "font"
X8_FONT_CANDIDATES = (FONT_DIR / "x8y12pxDenkiChip.ttf", BASE_DIR / "x8y12pxDenkiChip" / "x8y12pxDenkiChip.ttf")
X10_FONT_CANDIDATES = (FONT_DIR / "x10y12pxDonguriDuel.ttf", FONT_DIR / "x10y12pxDonguriDuel.otf")
COMMON_EVENT_LOGO = ASSETS_DIR / "common" / "logo_event.png"
TEMPLATES_JSON = BASE_DIR / "templates.json"

STANDARD_LIMITS = {
    "name": 6,
    "attribute": 4,
    "skill": 8,
    "phrase": 12,
    "habitat": 7,
    "hp": 4,
    "skill_label": 5,
    "phrase_label": 5,
    "habitat_label": 5,
    "description": 52,
}
MOJAOKUN_LIMITS = {**STANDARD_LIMITS, "skill": 8, "phrase": 18, "description": 92}


class CardError(ValueError):
    pass


@dataclass(frozen=True)
class TextLayout:
    name_xy: tuple[int, int]
    name_width: int
    attribute_xy: tuple[int, int] = (505, 863)
    label_xy: dict[str, tuple[int, int]] = field(default_factory=lambda: {
        "skill_label": (20, 877),
        "phrase_label": (20, 1059),
        "habitat_label": (20, 1241),
    })
    value_xy: dict[str, tuple[int, int]] = field(default_factory=lambda: {
        "skill": (7, 939),
        "phrase": (7, 1118),
        "habitat": (62, 1300),
    })
    skill_font_size: int = 57
    phrase_font_size: int = 75
    habitat_font_size: int = 75
    skill_line_height: int | None = None
    phrase_line_height: int | None = None
    habitat_line_height: int | None = None
    body_xy: tuple[int, int] = (512, 977)
    body_width: int = 515
    body_font_size: int = 64
    body_line_height: int = 70
    hp_xy: tuple[int, int] = (505, 1325)
    hp_value_xy: tuple[int, int] | None = None
    hp_value_width: int | None = None
    footer_box: tuple[int, int, int, int] = (28, 1379, 110, 110)


@dataclass(frozen=True)
class CardTemplate:
    id: str
    label: str
    figma_node: str
    background_color: str
    frame_border_color: str
    arrow_color: str
    text_color: str
    hp_fill: str | None
    hp_border_color: str
    page_background_path: Path | None
    background_path: Path
    character_path: Path | None
    image_box: tuple[int, int, int, int]
    character_box: tuple[int, int, int, int] | None
    layout: TextLayout
    defaults: dict[str, str]
    limits: dict[str, int] = field(default_factory=lambda: dict(STANDARD_LIMITS))
    event_logo_path: Path | None = COMMON_EVENT_LOGO
    footer_logo_path: Path | None = None
    badge_character_path: Path | None = None
    badge_image_path: Path | None = None
    badge_variant: str = "normal"
    show_badge: bool = False


@dataclass(frozen=True)
class CardData:
    template: str
    name: str
    attribute: str
    skill: str
    phrase: str
    habitat: str
    description: str
    hp: str
    skill_label: str = "とくぎ"
    phrase_label: str = "くちぐせ"
    habitat_label: str = "せいそくち"
    skill_font_size: int | None = None
    phrase_font_size: int | None = None
    habitat_font_size: int | None = None
    background_image: str | None = None
    character_image: str | None = None


def asset(path: str) -> Path:
    return BASE_DIR / path


def tuple2(value: list[int] | tuple[int, int]) -> tuple[int, int]:
    return int(value[0]), int(value[1])


def tuple4(value: list[int] | tuple[int, int, int, int] | None) -> tuple[int, int, int, int] | None:
    if value is None:
        return None
    return int(value[0]), int(value[1]), int(value[2]), int(value[3])


def optional_asset_path(value: str | None) -> Path | None:
    if value in (None, ""):
        return None
    return asset(str(value))


def build_text_layout(raw: dict[str, Any]) -> TextLayout:
    return TextLayout(
        name_xy=tuple2(raw["name_xy"]),
        name_width=int(raw["name_width"]),
        attribute_xy=tuple2(raw.get("attribute_xy", [505, 863])),
        label_xy={key: tuple2(value) for key, value in raw.get("label_xy", {}).items()} or {
            "skill_label": (20, 877),
            "phrase_label": (20, 1059),
            "habitat_label": (20, 1241),
        },
        value_xy={key: tuple2(value) for key, value in raw.get("value_xy", {}).items()} or {
            "skill": (7, 939),
            "phrase": (7, 1118),
            "habitat": (62, 1300),
        },
        skill_font_size=int(raw.get("skill_font_size", 57)),
        phrase_font_size=int(raw.get("phrase_font_size", 75)),
        habitat_font_size=int(raw.get("habitat_font_size", 75)),
        skill_line_height=raw.get("skill_line_height"),
        phrase_line_height=raw.get("phrase_line_height"),
        habitat_line_height=raw.get("habitat_line_height"),
        body_xy=tuple2(raw.get("body_xy", [512, 977])),
        body_width=int(raw.get("body_width", 515)),
        body_font_size=int(raw.get("body_font_size", 64)),
        body_line_height=int(raw.get("body_line_height", 70)),
        hp_xy=tuple2(raw.get("hp_xy", [505, 1325])),
        hp_value_xy=tuple2(raw["hp_value_xy"]) if "hp_value_xy" in raw else None,
        hp_value_width=int(raw["hp_value_width"]) if "hp_value_width" in raw else None,
        footer_box=tuple4(raw.get("footer_box", [28, 1379, 110, 110])),
    )


def build_template(raw: dict[str, Any]) -> CardTemplate:
    colors = raw["colors"]
    assets = raw["assets"]
    boxes = raw["boxes"]
    return CardTemplate(
        id=str(raw["id"]),
        label=str(raw["label"]),
        figma_node=str(raw["figma_node"]),
        background_color=str(colors["background"]),
        frame_border_color=str(colors["frame_border"]),
        arrow_color=str(colors["arrow"]),
        text_color=str(colors["text"]),
        hp_fill=colors.get("hp_fill"),
        hp_border_color=str(colors["hp_border"]),
        page_background_path=optional_asset_path(assets.get("page_background")),
        background_path=asset(str(assets["background"])),
        character_path=optional_asset_path(assets.get("character")),
        image_box=tuple4(boxes["image"]),
        character_box=tuple4(boxes.get("character")),
        layout=build_text_layout(raw["layout"]),
        defaults={key: str(value) for key, value in raw["defaults"].items()},
        limits={key: int(value) for key, value in raw.get("limits", STANDARD_LIMITS).items()},
        event_logo_path=optional_asset_path(assets.get("event_logo")),
        footer_logo_path=optional_asset_path(assets.get("footer_logo")),
        badge_character_path=optional_asset_path(assets.get("badge_character")),
        badge_image_path=optional_asset_path(assets.get("badge_image")),
        badge_variant=str(raw.get("badge_variant", "normal")),
        show_badge=bool(raw.get("show_badge", False)),
    )


def load_templates(path: Path = TEMPLATES_JSON) -> dict[str, CardTemplate]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CardError(f"テンプレートJSONを読み込めません: {path} ({exc})") from exc
    raw_templates = payload.get("templates")
    if not isinstance(raw_templates, list) or not raw_templates:
        raise CardError("templates.json の `templates` は1件以上の配列にしてください。")
    templates = {template.id: template for template in (build_template(raw) for raw in raw_templates)}
    if len(templates) != len(raw_templates):
        raise CardError("templates.json に重複したテンプレートIDがあります。")
    if "slime" not in templates:
        raise CardError("templates.json には互換用の `slime` テンプレートが必要です。")
    return templates


TEMPLATES: dict[str, CardTemplate] = load_templates()


def require_file(path: Path, label: str) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"{label} が見つかりません: {path}")
    return path


def resolve_path(value: str | None, base: Path, default: Path) -> Path:
    if not value:
        return default
    path = Path(value)
    return (path if path.is_absolute() else base / path).resolve()


def find_font(candidates: tuple[Path, ...], label: str) -> Path:
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(f"{label} が見つかりません。gen-png/font/ に配置してください。")


def load_fonts(allow_font_fallback: bool) -> dict[str, ImageFont.FreeTypeFont]:
    x8 = find_font(X8_FONT_CANDIDATES, "x8y12pxDenkiChip フォント")
    try:
        x10 = find_font(X10_FONT_CANDIDATES, "x10y12pxDonguriDuel フォント")
    except FileNotFoundError:
        if not allow_font_fallback:
            raise
        x10 = x8
    fonts = {"body_48": ImageFont.truetype(str(x8), 48), "body_64": ImageFont.truetype(str(x8), 64)}
    for size in (45, 50, 57, 75, 100, 128):
        fonts[f"x10_{size}"] = ImageFont.truetype(str(x10), size)
    return fonts


def x10_font(fonts: dict[str, ImageFont.FreeTypeFont], size: int) -> ImageFont.FreeTypeFont:
    key = f"x10_{size}"
    if key not in fonts:
        fonts[key] = fonts["x10_128"].font_variant(size=size)
    return fonts[key]


def as_text(value: Any, field_name: str) -> str:
    if value is None:
        raise CardError(f"必須項目 `{field_name}` がありません。")
    text = str(value)
    if not text:
        raise CardError(f"必須項目 `{field_name}` が空です。")
    return text


def optional_font_size(value: Any, field_name: str) -> int | None:
    if value in (None, ""):
        return None
    try:
        size = int(value)
    except (TypeError, ValueError) as exc:
        raise CardError(f"`{field_name}` は整数で指定してください。") from exc
    if not 20 <= size <= 128:
        raise CardError(f"`{field_name}` は20から128の範囲で指定してください。")
    return size


def parse_card(raw: dict[str, Any]) -> CardData:
    template_id = str(raw.get("template", "slime"))
    if template_id not in TEMPLATES:
        raise CardError(f"未知の template `{template_id}` です。利用可能: {', '.join(TEMPLATES)}")
    template = TEMPLATES[template_id]
    defaults = template.defaults
    card = CardData(
        template=template_id,
        name=as_text(raw.get("name", defaults["name"]), "name"),
        attribute=as_text(raw.get("attribute", defaults["attribute"]), "attribute"),
        skill=as_text(raw.get("skill", defaults["skill"]), "skill"),
        phrase=as_text(raw.get("phrase", defaults["phrase"]), "phrase"),
        habitat=as_text(raw.get("habitat", defaults["habitat"]), "habitat"),
        description=as_text(raw.get("description", defaults["description"]), "description"),
        hp=as_text(raw.get("hp", defaults["hp"]), "hp"),
        skill_label=str(raw.get("skill_label", "とくぎ")),
        phrase_label=str(raw.get("phrase_label", "くちぐせ")),
        habitat_label=str(raw.get("habitat_label", "せいそくち")),
        skill_font_size=optional_font_size(raw.get("skill_font_size"), "skill_font_size"),
        phrase_font_size=optional_font_size(raw.get("phrase_font_size"), "phrase_font_size"),
        habitat_font_size=optional_font_size(raw.get("habitat_font_size"), "habitat_font_size"),
        background_image=raw.get("background_image"),
        character_image=raw.get("character_image"),
    )
    validate_card_lengths(card, template)
    return card


def validate_card_lengths(card: CardData, template: CardTemplate) -> None:
    values = {
        "name": card.name,
        "attribute": card.attribute,
        "skill": card.skill,
        "phrase": card.phrase,
        "habitat": card.habitat,
        "hp": card.hp,
        "skill_label": card.skill_label,
        "phrase_label": card.phrase_label,
        "habitat_label": card.habitat_label,
        "description": card.description,
    }
    for field_name, value in values.items():
        limit = template.limits[field_name]
        length = len(value.replace("\n", ""))
        if length > limit:
            raise CardError(f"`{field_name}` は {limit} 文字以内にしてください。現在は {length} 文字です。")


def parse_cards_payload(payload: Any) -> list[CardData]:
    if isinstance(payload, dict) and "cards" in payload:
        raw_cards = payload["cards"]
        if not isinstance(raw_cards, list) or not raw_cards:
            raise CardError("`cards` は1件以上の配列にしてください。")
    elif isinstance(payload, dict):
        raw_cards = [payload]
    else:
        raise CardError("入力JSONはカードオブジェクト、または `cards` 配列を持つオブジェクトにしてください。")
    cards = []
    for index, raw in enumerate(raw_cards, 1):
        if not isinstance(raw, dict):
            raise CardError(f"{index}件目のカードがオブジェクトではありません。")
        try:
            cards.append(parse_card(raw))
        except CardError as exc:
            raise CardError(f"{index}件目: {exc}") from exc
    return cards


def load_cards(input_path: Path) -> list[CardData]:
    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CardError(f"JSONを読み込めません: {input_path} ({exc})") from exc
    return parse_cards_payload(payload)


def open_rgba(path: Path) -> Image.Image:
    require_file(path, "画像")
    return ImageOps.exif_transpose(Image.open(path)).convert("RGBA")


def paste_cover(canvas: Image.Image, image_path: Path, box: tuple[int, int, int, int]) -> None:
    x, y, width, height = box
    with open_rgba(image_path) as image:
        fitted = ImageOps.fit(image, (width, height), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
        canvas.alpha_composite(fitted, (x, y))


def paste_contain(canvas: Image.Image, image_path: Path, box: tuple[int, int, int, int], rotate_180: bool = False) -> None:
    x, y, width, height = box
    with open_rgba(image_path) as image:
        image.thumbnail((width, height), Image.Resampling.LANCZOS)
        if rotate_180:
            image = ImageOps.mirror(image)
        layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        layer.alpha_composite(image, ((width - image.width) // 2, (height - image.height) // 2))
        canvas.alpha_composite(layer, (x, y))


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines = []
    for paragraph in text.splitlines() or [""]:
        current = ""
        for char in paragraph:
            candidate = current + char
            bbox = draw.textbbox((0, 0), candidate, font=font)
            if current and bbox[2] - bbox[0] > max_width:
                lines.append(current)
                current = char
            else:
                current = candidate
        lines.append(current)
    return lines


def draw_text_box(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font: ImageFont.FreeTypeFont, fill: str, width: int | None = None, line_height: int | None = None) -> None:
    if width is None:
        draw.text(xy, text, font=font, fill=fill)
        return
    for offset, line in enumerate(wrap_text(draw, text, font, width)):
        draw.text((xy[0], xy[1] + offset * (line_height or round(font.size * 1.1))), line, font=font, fill=fill)


def draw_single_line(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font: ImageFont.FreeTypeFont, fill: str, width: int | None = None, center: bool = False) -> None:
    x, y = xy
    if center and width is not None:
        bbox = draw.textbbox((0, 0), text, font=font)
        x += (width - (bbox[2] - bbox[0])) // 2
    draw.text((x, y), text, font=font, fill=fill)


def draw_arrow(draw: ImageDraw.ImageDraw, x: int, y: int, color: str) -> None:
    draw.polygon([(x, y), (x + 384, y), (x + 460, y + 46), (x + 384, y + 93), (x, y + 93)], fill=color)


def draw_fixed_badge(canvas: Image.Image, draw: ImageDraw.ImageDraw, fonts: dict[str, ImageFont.FreeTypeFont], template: CardTemplate) -> None:
    if template.badge_image_path:
        paste_cover(canvas, template.badge_image_path, (875, 15, 143, 95))
        return
    if template.badge_variant == "gold":
        for x in range(875, 1018):
            ratio = (x - 875) / 143
            if ratio < 0.2:
                color = (191 + int(64 * ratio / 0.2), 161 + int(80 * ratio / 0.2), 62 + int(77 * ratio / 0.2), 255)
            else:
                color = (255 - int(64 * (ratio - 0.2) / 0.8), 241 - int(80 * (ratio - 0.2) / 0.8), 139 - int(77 * (ratio - 0.2) / 0.8), 255)
            draw.line((x, 15, x, 110), fill=color)
        draw.rounded_rectangle((875, 15, 1018, 110), radius=10, outline="#bfa13e", width=1)
        draw.polygon([(883, 23), (937, 23), (974, 102), (883, 102)], fill="#ffffff")
        draw.rounded_rectangle((986, 23, 1010, 35), radius=5, fill="#ffffff")
        logo_fill = "#bfa13e"
    else:
        draw.rounded_rectangle((875, 15, 1018, 110), radius=10, fill="#eeeeee")
        draw.polygon([(883, 23), (937, 23), (974, 102), (883, 102)], fill="#6bb230")
        draw.rounded_rectangle((986, 23, 1010, 35), radius=5, fill="#6bb230")
        logo_fill = "#ffffff"
    draw.text((888, 82), "ShibaLab", font=fonts["x10_50"].font_variant(size=10), fill=logo_fill)
    if template.badge_character_path:
        paste_contain(canvas, template.badge_character_path, (978, 50, 38, 51), rotate_180=True)


def render_card(card: CardData, input_base: Path, fonts: dict[str, ImageFont.FreeTypeFont]) -> Image.Image:
    template = TEMPLATES[card.template]
    background = resolve_path(card.background_image, input_base, template.background_path)
    character = resolve_path(card.character_image, input_base, template.character_path) if (card.character_image or template.character_path) else None
    for label, path in {"背景画像": background, "イベントロゴ": template.event_logo_path}.items():
        if path:
            require_file(path, label)
    if character:
        require_file(character, "キャラ画像")

    canvas = Image.new("RGBA", FIGMA_CANVAS_SIZE, template.background_color)
    draw = ImageDraw.Draw(canvas)
    if template.page_background_path:
        paste_cover(canvas, template.page_background_path, (0, 0, 1056, 1506))
    paste_cover(canvas, background, template.image_box)
    if character and template.character_box:
        paste_cover(canvas, character, template.character_box)
    if template.event_logo_path:
        paste_contain(canvas, template.event_logo_path, (33, -8, 416, 139))
    if template.show_badge:
        draw_fixed_badge(canvas, draw, fonts, template)
    draw.rectangle((33, 117, 1018, 672), outline=template.frame_border_color, width=13)

    layout = template.layout
    draw_single_line(draw, layout.name_xy, card.name, fonts["x10_128"], template.text_color, width=layout.name_width, center=True)
    draw_single_line(draw, layout.attribute_xy, card.attribute, fonts["x10_100"], template.text_color)
    for y in (927, 1109, 1291):
        draw_arrow(draw, 0, y, template.arrow_color)
    draw_text_box(draw, layout.label_xy["skill_label"], card.skill_label, fonts["x10_50"], template.text_color)
    draw_text_box(draw, layout.label_xy["phrase_label"], card.phrase_label, fonts["x10_50"], template.text_color)
    draw_text_box(draw, layout.label_xy["habitat_label"], card.habitat_label, fonts["x10_50"], template.text_color)
    skill_size = card.skill_font_size or layout.skill_font_size
    phrase_size = card.phrase_font_size or layout.phrase_font_size
    habitat_size = card.habitat_font_size or layout.habitat_font_size
    if "\n" in card.skill:
        draw_text_box(draw, layout.value_xy["skill"], card.skill, x10_font(fonts, skill_size), template.text_color, width=389, line_height=layout.skill_line_height or 66)
    else:
        draw_single_line(draw, layout.value_xy["skill"], card.skill, x10_font(fonts, skill_size), template.text_color)
    if "\n" in card.phrase:
        draw_text_box(draw, layout.value_xy["phrase"], card.phrase, x10_font(fonts, phrase_size), template.text_color, width=390, line_height=layout.phrase_line_height or (58 if phrase_size < 60 else None))
    else:
        draw_single_line(draw, layout.value_xy["phrase"], card.phrase, x10_font(fonts, phrase_size), template.text_color)
    if "\n" in card.habitat or layout.habitat_line_height:
        draw_text_box(draw, layout.value_xy["habitat"], card.habitat, x10_font(fonts, habitat_size), template.text_color, width=430, line_height=layout.habitat_line_height)
    else:
        draw_single_line(draw, layout.value_xy["habitat"], card.habitat, x10_font(fonts, habitat_size), template.text_color)
    draw_text_box(draw, layout.body_xy, card.description, fonts[f"body_{layout.body_font_size}"], template.text_color, width=layout.body_width, line_height=layout.body_line_height)

    hp_fill = template.hp_fill or template.background_color
    draw.rectangle((477, 1315, 999, 1453), fill=hp_fill, outline=template.hp_border_color, width=10)
    if layout.hp_value_xy:
        draw_single_line(draw, layout.hp_xy, "HP:", fonts["x10_100"], template.text_color)
        draw_single_line(draw, layout.hp_value_xy, card.hp, fonts["x10_100"], template.text_color, width=layout.hp_value_width, center=bool(layout.hp_value_width))
    else:
        draw_single_line(draw, layout.hp_xy, f"HP:{card.hp}", fonts["x10_100"], template.text_color)
    if template.footer_logo_path:
        paste_contain(canvas, template.footer_logo_path, layout.footer_box)
    return canvas.crop((0, 0, CANVAS_SIZE[0], CANVAS_SIZE[1])).convert("RGB")


def save_outputs(images: list[Image.Image], output_pdf: Path, preview_dir: Path | None) -> None:
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    first, *rest = images
    first.save(output_pdf, "PDF", resolution=float(DPI), save_all=True, append_images=rest)
    if preview_dir is not None:
        preview_dir.mkdir(parents=True, exist_ok=True)
        for index, image in enumerate(images, 1):
            image.save(preview_dir / f"card_{index:03}.png", "PNG", dpi=(DPI, DPI))


def images_to_pdf_bytes(images: list[Image.Image]) -> bytes:
    buffer = BytesIO()
    first, *rest = images
    first.save(buffer, "PDF", resolution=float(DPI), save_all=True, append_images=rest)
    return buffer.getvalue()


def render_payload_to_pdf(payload: Any, input_base: Path, allow_font_fallback: bool = False) -> bytes:
    cards = parse_cards_payload(payload)
    fonts = load_fonts(allow_font_fallback)
    return images_to_pdf_bytes([render_card(card, input_base, fonts) for card in cards])


def template_summary(template: CardTemplate) -> dict[str, Any]:
    return {
        "id": template.id,
        "label": template.label,
        "figma_node": template.figma_node,
        "defaults": template.defaults,
        "default_font_sizes": {
            "skill_font_size": template.layout.skill_font_size,
            "phrase_font_size": template.layout.phrase_font_size,
            "habitat_font_size": template.layout.habitat_font_size,
        },
        "limits": template.limits,
    }


def create_app():
    from flask import Flask, Response, jsonify, render_template_string, request, send_file

    app = Flask(__name__)
    options = "".join(f'<option value="{t.id}">{t.label} ({t.id})</option>' for t in TEMPLATES.values())
    html = f"""<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>カードPDF生成</title><style>body{{font-family:system-ui,sans-serif;margin:0;background:#f4f4f4;color:#111}}main{{max-width:920px;margin:0 auto;padding:32px 20px}}form{{display:grid;gap:14px;background:#fff;padding:20px;border:1px solid #ddd}}label{{display:grid;gap:6px;font-weight:700}}input,textarea,select{{font:inherit;padding:10px;border:1px solid #aaa}}textarea{{min-height:130px}}button{{width:fit-content;padding:10px 18px;font:inherit;font-weight:700;cursor:pointer}}</style></head><body><main><h1>カードPDF生成</h1><form method="post" action="/generate"><label>テンプレート<select name="template">{options}</select></label><label>名前<input name="name" placeholder="テンプレート既定"></label><label>属性<input name="attribute" placeholder="テンプレート既定"></label><label>特技<input name="skill" placeholder="テンプレート既定"></label><label>特技フォントサイズ<input name="skill_font_size" type="number" min="20" max="128" placeholder="テンプレート既定"></label><label>口癖<input name="phrase" placeholder="テンプレート既定"></label><label>口癖フォントサイズ<input name="phrase_font_size" type="number" min="20" max="128" placeholder="テンプレート既定"></label><label>生息地<input name="habitat" placeholder="テンプレート既定"></label><label>生息地フォントサイズ<input name="habitat_font_size" type="number" min="20" max="128" placeholder="テンプレート既定"></label><label>説明<textarea name="description" placeholder="テンプレート既定"></textarea></label><label>HP<input name="hp" placeholder="テンプレート既定"></label><label>背景画像パス 任意<input name="background_image"></label><label>キャラ画像パス 任意<input name="character_image"></label><button type="submit">PDF生成</button></form></main></body></html>"""

    def error_response(exc: Exception, status: int = 400):
        return jsonify({"ok": False, "error": str(exc)}), status

    @app.get("/")
    def index():
        return render_template_string(html)

    @app.post("/generate")
    def generate_from_form():
        payload = {
            key: request.form.get(key)
            for key in (
                "template",
                "name",
                "attribute",
                "skill",
                "skill_font_size",
                "phrase",
                "phrase_font_size",
                "habitat",
                "habitat_font_size",
                "description",
                "hp",
            )
            if request.form.get(key)
        }
        for key in ("background_image", "character_image"):
            if request.form.get(key):
                payload[key] = request.form.get(key)
        try:
            pdf = render_payload_to_pdf(payload, BASE_DIR)
        except (CardError, FileNotFoundError, OSError) as exc:
            return Response(str(exc), status=400, mimetype="text/plain; charset=utf-8")
        return send_file(BytesIO(pdf), mimetype="application/pdf", as_attachment=True, download_name="card.pdf")

    @app.get("/api/v1/")
    def api_index():
        return jsonify({"ok": True, "endpoints": {"GET /api/v1/": "API情報", "GET /api/v1/health": "ヘルスチェック", "GET /api/v1/templates": "テンプレート一覧", "POST /api/v1/generate": "PDF生成"}, "templates": list(TEMPLATES)})

    @app.get("/api/v1/health")
    def api_health():
        return jsonify({"ok": True})

    @app.get("/api/v1/templates")
    def api_templates():
        return jsonify({"ok": True, "templates": [template_summary(template) for template in TEMPLATES.values()]})

    @app.post("/api/v1/generate")
    def api_generate():
        payload = request.get_json(silent=True)
        if payload is None:
            return error_response(CardError("JSONボディを送信してください。"))
        try:
            pdf = render_payload_to_pdf(payload, BASE_DIR)
        except (CardError, FileNotFoundError, OSError) as exc:
            return error_response(exc)
        return send_file(BytesIO(pdf), mimetype="application/pdf", as_attachment=True, download_name="card.pdf")

    return app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Figmaカードデザインから文字・画像差し替えPDFを生成します。")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="カード情報JSON")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="出力PDF")
    parser.add_argument("--preview-dir", type=Path, help="確認用PNGの出力先")
    parser.add_argument("--serve", action="store_true", help="HTTPサーバーを起動します。")
    parser.add_argument("--host", default="0.0.0.0", help="HTTPサーバーのホスト")
    parser.add_argument("--port", type=int, default=8080, help="HTTPサーバーのポート")
    parser.add_argument("--allow-font-fallback", action="store_true", help="x10フォントが無い場合にx8で代替します。")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.serve:
        create_app().run(host=args.host, port=args.port)
        return
    input_path = args.input.resolve()
    require_file(input_path, "入力JSON")
    cards = load_cards(input_path)
    fonts = load_fonts(args.allow_font_fallback)
    images = [render_card(card, input_path.parent, fonts) for card in cards]
    save_outputs(images, args.output.resolve(), args.preview_dir.resolve() if args.preview_dir else None)
    print(f"cards={len(images)}")
    print(f"pdf={args.output.resolve()}")
    if args.preview_dir:
        print(f"preview_dir={args.preview_dir.resolve()}")


if __name__ == "__main__":
    main()
