#!/usr/bin/env python3
"""Generate self-contained profile visuals for github.com/Luics415.

The README only loads files stored in the profile repository. Public GitHub
metadata is fetched while generating, never while somebody views the profile.
Use --offline to regenerate deterministically from data/profile-snapshot.json.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import os
import re
import textwrap
import time
import urllib.error
import urllib.request
import base64
from copy import deepcopy
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
DATA = ROOT / "data"
README = ROOT / "README.md"
ICON_DIR = ASSETS / "icons"
SOCIAL_ICON_DIR = ICON_DIR / "social"
ANCHOR_PATH = ASSETS / "brand" / "anchor.png"

WIDTH = 900
CHESS_ORIGIN = (82, 170)
CHESS_CELL = 40
BG = "#020611"
SURFACE = "#06162B"
SURFACE_2 = "#0D2A49"
INK = "#FAFDFF"
MUTED = "#D2E6F6"
POWDER = "#E2F2FF"
CYAN = "#00E7FF"
MAGENTA = "#FF23C8"
WINE = "#C41A68"
GRID = "#215377"
GREEN = "#35F59A"
ORANGE = "#FFD04D"
GITHUB = "#FFFFFF"
WHATSAPP = "#25D366"

SOCIAL_ICON_FILES = {
    "GitHub": "github",
    "WhatsApp": "whatsapp",
    "Ubicación": "location",
}

TECH_COLORS = {
    "Java": "#FF3F87",
    "HTML": "#FF693A",
    "CSS": "#24ADFF",
    "C": "#B7E1FF",
    "C++": "#329DFF",
    "Sass": "#FF3FBD",
    "JavaScript": "#FFE600",
    "TypeScript": "#1FA8FF",
    "C#": "#A454FF",
    "Python": "#23E1FF",
    "PHP": "#8784FF",
    "Kotlin": "#FF1FB1",
}

BRAND_ICON_FILES = {
    "Java": "java-original",
    "HTML": "html5-original",
    "CSS": "css3-original",
    "C": "c-original",
    "C++": "cplusplus-original",
    "Sass": "sass-original",
    "JavaScript": "javascript-original",
    "TypeScript": "typescript-original",
    "C#": "csharp-original",
    "Python": "python-original",
    "PHP": "php-original",
    "Kotlin": "kotlin-original",
}

PIECE_GLYPHS = {
    "K": "♔",
    "Q": "♕",
    "R": "♖",
    "B": "♗",
    "N": "♘",
    "P": "♙",
    "k": "♚",
    "q": "♛",
    "r": "♜",
    "b": "♝",
    "n": "♞",
    "p": "♟",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def mix(a: str, b: str, amount: float) -> tuple[int, int, int]:
    aa, bb = hex_rgb(a), hex_rgb(b)
    return tuple(round(aa[i] * (1 - amount) + bb[i] * amount) for i in range(3))


def mix_hex(a: str, b: str, amount: float) -> str:
    return "#" + "".join(f"{channel:02X}" for channel in mix(a, b, amount))


def rgba(value: str, alpha: int) -> tuple[int, int, int, int]:
    return (*hex_rgb(value), alpha)


def font_candidates(kind: str) -> list[str]:
    windows = Path("C:/Windows/Fonts")
    linux = Path("/usr/share/fonts/truetype/dejavu")
    candidates = {
        "regular": [
            windows / "segoeui.ttf",
            linux / "DejaVuSans.ttf",
        ],
        "bold": [
            windows / "seguisb.ttf",
            windows / "segoeuib.ttf",
            linux / "DejaVuSans-Bold.ttf",
        ],
        "black": [
            windows / "seguibl.ttf",
            windows / "ariblk.ttf",
            linux / "DejaVuSans-Bold.ttf",
        ],
        "mono": [
            windows / "consola.ttf",
            linux / "DejaVuSansMono.ttf",
        ],
        "symbol": [
            windows / "seguisym.ttf",
            linux / "DejaVuSans.ttf",
        ],
    }
    return [str(path) for path in candidates[kind]]


def get_font(size: int, kind: str = "regular") -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in font_candidates(kind):
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    value: str,
    size: int,
    fill: str | tuple[int, ...] = INK,
    kind: str = "regular",
    anchor: str = "la",
    stroke_width: int = 0,
    stroke_fill: str | None = None,
) -> None:
    draw.text(
        xy,
        value,
        font=get_font(size, kind),
        fill=fill,
        anchor=anchor,
        stroke_width=stroke_width,
        stroke_fill=stroke_fill,
    )


def text_width(value: str, size: int, kind: str = "regular") -> float:
    font = get_font(size, kind)
    box = font.getbbox(value)
    return box[2] - box[0]


def wrapped(value: str, width: int) -> list[str]:
    return textwrap.wrap(value, width=width, break_long_words=False) or [""]


def base_canvas(height: int, code: str) -> Image.Image:
    image = Image.new("RGB", (WIDTH, height), BG)
    draw = ImageDraw.Draw(image)
    top, bottom = hex_rgb("#06385C"), hex_rgb(BG)
    for y in range(height):
        t = y / max(1, height - 1)
        color = tuple(round(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        draw.line((0, y, WIDTH, y), fill=color)

    glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((-180, -260, 390, 310), fill=rgba(CYAN, 78))
    gd.ellipse((610, -170, 1080, 320), fill=rgba(MAGENTA, 68))
    gd.ellipse((530, height - 270, 1000, height + 210), fill=rgba(WINE, 82))
    glow = glow.filter(ImageFilter.GaussianBlur(70))
    image = Image.alpha_composite(image.convert("RGBA"), glow).convert("RGB")
    draw = ImageDraw.Draw(image)

    for x in range(30, WIDTH, 60):
        draw.line((x, 0, x, height), fill=GRID, width=1)
    for y in range(30, height, 60):
        draw.line((0, y, WIDTH, y), fill=GRID, width=1)

    draw.rounded_rectangle((18, 18, WIDTH - 18, height - 18), 26, outline="#4A9BC7", width=2)
    draw.line((44, 47, 116, 47), fill=CYAN, width=3)
    draw.line((WIDTH - 116, 47, WIDTH - 44, 47), fill=MAGENTA, width=3)
    draw_text(draw, (46, height - 34), f"LUICS415 // {code}", 13, MUTED, "mono", "ls")
    draw_text(draw, (WIDTH - 46, height - 34), "LOCAL · REPRODUCIBLE · GITHUB READY", 13, MUTED, "mono", "rs")
    return image


def panel(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    accent: str = CYAN,
    radius: int = 22,
    width: int = 2,
) -> None:
    draw.rounded_rectangle(
        box,
        radius,
        fill=mix(SURFACE, accent, 0.11),
        outline=mix(SURFACE, accent, 0.88),
        width=width,
    )
    x1, y1, x2, _ = box
    draw.line((x1 + 22, y1, min(x1 + 96, x2 - 22), y1), fill=accent, width=3)


def chip(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    value: str,
    accent: str = CYAN,
    size: int = 16,
    pad_x: int = 16,
    pad_y: int = 9,
) -> tuple[int, int, int, int]:
    x, y = xy
    w = math.ceil(text_width(value, size, "bold")) + pad_x * 2
    h = size + pad_y * 2 + 2
    draw.rounded_rectangle((x, y, x + w, y + h), h // 2, fill=mix(SURFACE, accent, 0.18), outline=mix(SURFACE, accent, 0.72), width=1)
    draw_text(draw, (x + w / 2, y + h / 2), value, size, POWDER, "bold", "mm")
    return (x, y, x + w, y + h)


def save_gif(
    frames: list[Image.Image],
    durations: list[int],
    path: Path,
    colors: int = 96,
) -> None:
    if len(frames) != len(durations):
        raise ValueError(f"{path.name}: frame and duration counts differ")
    sample_width = 300
    sampled = [
        frame.resize(
            (sample_width, max(1, round(frame.height * sample_width / frame.width))),
            Image.Resampling.LANCZOS,
        )
        for frame in frames
    ]
    strip_height = sum(frame.height for frame in sampled)
    strip = Image.new("RGB", (sample_width, strip_height), BG)
    cursor = 0
    for frame in sampled:
        strip.paste(frame, (0, cursor))
        cursor += frame.height
    palette = strip.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
    encoded = [
        frame.convert("RGB").quantize(palette=palette, dither=Image.Dither.NONE)
        for frame in frames
    ]
    encoded[0].save(
        path,
        save_all=True,
        append_images=encoded[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )


def api_json(url: str, token: str | None, retries: int = 3) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Luics415-profile-visual-generator",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    for attempt in range(retries):
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            retryable = error.code == 429 or 500 <= error.code < 600
            if not retryable or attempt == retries - 1:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == retries - 1:
                raise
        time.sleep(2**attempt)


def repo_is_language_candidate(repo: dict[str, Any], config: dict[str, Any]) -> bool:
    name = repo["name"]
    if repo.get("fork") or repo.get("archived") or repo.get("disabled"):
        return False
    if name in config["language_excludes"]:
        return False
    if any(name.startswith(prefix) for prefix in config["language_exclude_prefixes"]):
        return False
    return True


def project_score(repo: dict[str, Any], config: dict[str, Any]) -> float:
    name = repo["name"]
    if (
        repo.get("fork")
        or repo.get("archived")
        or repo.get("disabled")
        or name in config["project_excludes"]
    ):
        return -10_000
    pushed = repo.get("pushed_at") or repo.get("updated_at") or "1970-01-01T00:00:00Z"
    try:
        age_days = max(
            0,
            (
                datetime.now(timezone.utc)
                - datetime.fromisoformat(pushed.replace("Z", "+00:00"))
            ).days,
        )
    except ValueError:
        age_days = 3650
    recency = max(0, 50 - min(age_days, 365) / 365 * 50)
    description = 15 if repo.get("description") else 0
    stars = min(20, int(repo.get("stargazers_count", 0)) * 8)
    size = min(18, math.log10(max(1, int(repo.get("size", 0)))) * 6)
    homepage = 4 if repo.get("homepage") else 0
    try:
        preference = max(0, 52 - config["featured_priority"].index(name) * 5)
    except ValueError:
        preference = 0
    weak_name = -22 if re.search(r"(test|demo|copy|edition|practice)", name, re.I) else 0
    return recency + description + stars + size + homepage + preference + weak_name


def fetch_snapshot(config: dict[str, Any]) -> dict[str, Any]:
    username = config["username"]
    token = os.getenv("GITHUB_TOKEN")
    repos: list[dict[str, Any]] = []
    page = 1
    while True:
        url = (
            f"https://api.github.com/users/{username}/repos"
            f"?per_page=100&page={page}&sort=updated&type=owner"
        )
        batch = api_json(url, token)
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    technologies = config["technologies"]
    language_bytes = {name: 0 for name in technologies}
    language_repo_counts = {name: 0 for name in technologies}
    used_repositories: list[str] = []
    latest = "1970-01-01T00:00:00Z"
    for repo in sorted(repos, key=lambda item: item["name"].casefold()):
        if not repo_is_language_candidate(repo, config):
            continue
        languages = api_json(repo["languages_url"], token)
        if not languages and repo.get("language") in technologies:
            raise RuntimeError(
                "GitHub returned an empty language map for "
                f"{repo['name']} even though its primary language is "
                f"{repo['language']}."
            )
        counted = False
        for technology in technologies:
            amount = int(languages.get(technology, 0))
            language_bytes[technology] += amount
            if amount > 0:
                language_repo_counts[technology] += 1
            counted = counted or amount > 0
        if counted:
            used_repositories.append(repo["name"])
            latest = max(latest, repo.get("pushed_at") or repo.get("updated_at") or latest)

    ranked = sorted(repos, key=lambda item: project_score(item, config), reverse=True)
    eligible = [repo for repo in ranked if project_score(repo, config) >= 0]
    featured_limit = int(config.get("featured_limit", 6))
    selected_repositories = eligible[:featured_limit]
    selected_names = {repo["name"] for repo in selected_repositories}
    by_name = {repo["name"]: repo for repo in eligible}
    required_names = [
        name for name in config.get("featured_required", []) if name in by_name
    ]
    if len(required_names) > featured_limit:
        raise ValueError("featured_required exceeds featured_limit")
    for required_name in required_names:
        required = by_name.get(required_name)
        if required is None or required_name in selected_names:
            continue
        if len(selected_repositories) >= featured_limit:
            removable = [
                repo
                for repo in selected_repositories
                if repo["name"] not in required_names
            ]
            if not removable:
                raise RuntimeError("No removable featured repository remains")
            removed = removable[-1]
            selected_repositories.remove(removed)
            selected_names.discard(removed["name"])
        selected_repositories.append(required)
        selected_names.add(required_name)
    priority = {
        name: index for index, name in enumerate(config.get("featured_priority", []))
    }
    required_order = {name: index for index, name in enumerate(required_names)}
    selected_repositories.sort(
        key=lambda repo: (
            0 if repo["name"] in required_order else 1,
            required_order.get(repo["name"], priority.get(repo["name"], 10_000)),
            -project_score(repo, config),
        )
    )
    selected: list[dict[str, Any]] = []
    for repo in selected_repositories:
        name = repo["name"]
        selected.append(
            {
                "name": name,
                "language": repo.get("language") or "Multi-stack",
                "stars": int(repo.get("stargazers_count", 0)),
                "updated_at": repo.get("pushed_at") or repo.get("updated_at"),
                "url": repo["html_url"],
                "description": (
                    config["project_copy"].get(name)
                    or repo.get("description")
                    or "Proyecto de software documentado en GitHub."
                ).strip(),
            }
        )

    signal_date = latest[:10] if latest and latest > "1970" else datetime.now(timezone.utc).date().isoformat()
    return {
        "signal_date": signal_date,
        "repositories_fetched": len(repos),
        "repositories_analyzed": sum(
            1 for repo in repos if repo_is_language_candidate(repo, config)
        ),
        "language_repositories": used_repositories,
        "language_bytes": language_bytes,
        "language_repo_counts": language_repo_counts,
        "projects": selected,
        "all_projects": [
            {
                "name": repo["name"],
                "language": repo.get("language") or "Multi-stack",
                "url": repo["html_url"],
                "description": (
                    config["project_copy"].get(repo["name"])
                    or repo.get("description")
                    or "Proyecto de software documentado en GitHub."
                ).strip(),
            }
            for repo in eligible
        ],
    }


def normalized_percentages(snapshot: dict[str, Any], technologies: Iterable[str]) -> dict[str, float]:
    values = {name: int(snapshot["language_bytes"].get(name, 0)) for name in technologies}
    total = sum(values.values())
    if not total:
        return {name: 0.0 for name in values}
    return {name: values[name] * 100 / total for name in values}


def brand_icon_path(technology: str, extension: str) -> Path:
    try:
        filename = BRAND_ICON_FILES[technology]
    except KeyError as error:
        raise KeyError(f"No official brand icon configured for {technology}") from error
    return ICON_DIR / f"{filename}.{extension}"


@lru_cache(maxsize=48)
def load_brand_icon(technology: str, size: int) -> Image.Image:
    path = brand_icon_path(technology, "png")
    if not path.exists():
        raise FileNotFoundError(
            f"Missing official logo {path}. Restore the vendored Devicon assets."
        )
    with Image.open(path) as source:
        icon = source.convert("RGBA")
    icon.thumbnail((size, size), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.alpha_composite(
        icon,
        ((size - icon.width) // 2, (size - icon.height) // 2),
    )
    return canvas


def draw_logo(
    image: Image.Image,
    center: tuple[int, int],
    technology: str,
    size: int = 72,
) -> None:
    cx, cy = center
    accent = TECH_COLORS.get(technology, CYAN)
    tile = size + 18
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (cx - tile // 2, cy - tile // 2, cx + tile // 2, cy + tile // 2),
        18,
        fill="#F7FAFC",
        outline=accent,
        width=2,
    )
    icon = load_brand_icon(technology, size)
    image.paste(icon, (cx - size // 2, cy - size // 2), icon)


def svg_brand_icon(technology: str, x: int, y: int, size: int) -> str:
    path = brand_icon_path(technology, "svg")
    if not path.exists():
        raise FileNotFoundError(f"Missing official logo {path}")
    source = path.read_text(encoding="utf-8")
    source = re.sub(r"<\?xml[^>]*>\s*", "", source)
    opening = re.search(r"<svg\b([^>]*)>", source, re.IGNORECASE)
    if opening is None:
        raise ValueError(f"Invalid SVG logo: {path}")
    view_box = re.search(r"viewBox=[\"']([^\"']+)[\"']", opening.group(1))
    if view_box is None:
        raise ValueError(f"SVG logo has no viewBox: {path}")
    inner = source[opening.end() : source.lower().rfind("</svg>")]
    return (
        f'<svg x="{x}" y="{y}" width="{size}" height="{size}" '
        f'viewBox="{html.escape(view_box.group(1))}" '
        f'preserveAspectRatio="xMidYMid meet">{inner}</svg>'
    )


@lru_cache(maxsize=12)
def load_social_icon(label: str, size: int) -> Image.Image:
    stem = SOCIAL_ICON_FILES[label]
    path = SOCIAL_ICON_DIR / f"{stem}.png"
    if not path.exists():
        raise FileNotFoundError(f"Missing social icon {path}")
    with Image.open(path) as source:
        alpha = source.convert("RGBA").getchannel("A")
    alpha.thumbnail((size, size), Image.Resampling.LANCZOS)
    color = {"GitHub": GITHUB, "WhatsApp": WHATSAPP, "Ubicación": MAGENTA}[label]
    icon = Image.new("RGBA", alpha.size, rgba(color, 255))
    icon.putalpha(alpha)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.alpha_composite(icon, ((size - icon.width) // 2, (size - icon.height) // 2))
    return canvas


def draw_social_icon(image: Image.Image, center: tuple[int, int], label: str, size: int = 30) -> None:
    icon = load_social_icon(label, size)
    image.paste(icon, (center[0] - size // 2, center[1] - size // 2), icon)


def svg_social_icon(label: str, x: int, y: int, size: int) -> str:
    stem = SOCIAL_ICON_FILES[label]
    path = SOCIAL_ICON_DIR / f"{stem}.svg"
    source = path.read_text(encoding="utf-8")
    opening = re.search(r"<svg\b([^>]*)>", source, re.IGNORECASE)
    view_box = re.search(r"viewBox=[\"']([^\"']+)[\"']", opening.group(1)) if opening else None
    if opening is None or view_box is None:
        raise ValueError(f"Invalid social SVG icon: {path}")
    inner = source[opening.end() : source.lower().rfind("</svg>")]
    color = {"GitHub": GITHUB, "WhatsApp": WHATSAPP, "Ubicación": MAGENTA}[label]
    return (
        f'<svg x="{x}" y="{y}" width="{size}" height="{size}" '
        f'viewBox="{html.escape(view_box.group(1))}" fill="{color}">{inner}</svg>'
    )


@lru_cache(maxsize=4)
def load_anchor(size: int) -> Image.Image:
    if not ANCHOR_PATH.exists():
        raise FileNotFoundError(f"Missing personal anchor icon {ANCHOR_PATH}")
    with Image.open(ANCHOR_PATH) as source:
        anchor = source.convert("RGB").resize((size, size), Image.Resampling.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    anchor.putalpha(mask)
    return anchor


def draw_anchor(image: Image.Image, center: tuple[int, int], size: int = 58) -> None:
    anchor = load_anchor(size)
    image.paste(anchor, (center[0] - size // 2, center[1] - size // 2), anchor)


def svg_anchor(x: int, y: int, size: int) -> str:
    encoded = base64.b64encode(ANCHOR_PATH.read_bytes()).decode("ascii")
    clip_id = "hero-anchor-clip"
    return (
        f'<defs><clipPath id="{clip_id}"><circle cx="{x + size / 2}" cy="{y + size / 2}" r="{size / 2}"/></clipPath></defs>'
        f'<image x="{x}" y="{y}" width="{size}" height="{size}" preserveAspectRatio="xMidYMid slice" '
        f'clip-path="url(#{clip_id})" href="data:image/png;base64,{encoded}"/>'
    )


def initial_board() -> dict[str, str]:
    board: dict[str, str] = {}
    for file_name, piece in zip("abcdefgh", "RNBQKBNR"):
        board[f"{file_name}1"] = piece
        board[f"{file_name}2"] = "P"
        board[f"{file_name}7"] = "p"
    for file_name, piece in zip("abcdefgh", "rnbqkbnr"):
        board[f"{file_name}8"] = piece
    return board


def apply_move(board: dict[str, str], source: str, target: str) -> None:
    piece = board.pop(source)
    board.pop(target, None)
    if piece.lower() == "k" and abs(ord(source[0]) - ord(target[0])) == 2:
        rank = source[1]
        if target[0] == "g":
            rook = board.pop(f"h{rank}")
            board[f"f{rank}"] = rook
        else:
            rook = board.pop(f"a{rank}")
            board[f"d{rank}"] = rook
    board[target] = piece


def square_center(square: str, origin: tuple[int, int], cell: int) -> tuple[float, float]:
    file_index = ord(square[0]) - ord("a")
    rank_index = 8 - int(square[1])
    return (
        origin[0] + file_index * cell + cell / 2,
        origin[1] + rank_index * cell + cell / 2,
    )


def draw_board(
    draw: ImageDraw.ImageDraw,
    board: dict[str, str],
    origin: tuple[int, int],
    cell: int,
    last_move: tuple[str, str] | None = None,
    moving: tuple[str, float, float] | None = None,
    mate: bool = False,
) -> None:
    ox, oy = origin
    board_size = cell * 8
    draw.rounded_rectangle((ox - 8, oy - 8, ox + board_size + 8, oy + board_size + 8), 18, fill="#08101D", outline="#3A5572", width=2)
    for rank in range(8):
        for file_index in range(8):
            x1, y1 = ox + file_index * cell, oy + rank * cell
            light = (file_index + rank) % 2 == 0
            fill = POWDER if light else "#356080"
            draw.rectangle((x1, y1, x1 + cell, y1 + cell), fill=fill)
    if last_move:
        for square in last_move:
            cx, cy = square_center(square, origin, cell)
            draw.rectangle(
                (cx - cell / 2 + 2, cy - cell / 2 + 2, cx + cell / 2 - 2, cy + cell / 2 - 2),
                outline=MAGENTA,
                width=4,
            )
    if mate:
        cx, cy = square_center("e8", origin, cell)
        for radius, color in ((cell * 0.44, WINE), (cell * 0.32, MAGENTA)):
            draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), outline=color, width=3)

    piece_font = get_font(round(cell * 0.82), "symbol")
    for square, piece in board.items():
        cx, cy = square_center(square, origin, cell)
        fill = "#F8FBFF" if piece.isupper() else "#09101A"
        stroke = "#31516B" if piece.isupper() else "#D572B7"
        draw.text(
            (cx, cy + 1),
            PIECE_GLYPHS[piece],
            font=piece_font,
            fill=fill,
            anchor="mm",
            stroke_width=1,
            stroke_fill=stroke,
        )
    if moving:
        piece, cx, cy = moving
        fill = "#F8FBFF" if piece.isupper() else "#09101A"
        stroke = "#31516B" if piece.isupper() else "#D572B7"
        draw.text(
            (cx, cy + 1),
            PIECE_GLYPHS[piece],
            font=piece_font,
            fill=fill,
            anchor="mm",
            stroke_width=1,
            stroke_fill=stroke,
        )

def draw_section_title(
    draw: ImageDraw.ImageDraw,
    eyebrow: str,
    title: str,
    subtitle: str,
    title_size: int = 46,
) -> None:
    draw_text(draw, (60, 58), eyebrow.upper(), 15, CYAN, "mono", "la")
    draw_text(draw, (60, 88), title, title_size, INK, "black", "la")
    draw_text(draw, (60, 88 + title_size + 9), subtitle, 20, MUTED, "regular", "la")


def render_hero(config: dict[str, Any]) -> Image.Image:
    height = 360
    base = base_canvas(height, "HERO")
    frames: list[Image.Image] = []
    durations: list[int] = []
    for index in range(24):
        phase = index / 24
        frame = base.copy()
        draw = ImageDraw.Draw(frame)
        draw_text(draw, (62, 62), "SOFTWARE ENGINEERING // PROFILE", 15, CYAN, "mono", "la")
        draw_text(draw, (62, 112), config["name"], 44, INK, "black", "la")
        draw_text(draw, (64, 178), config["role"], 27, POWDER, "bold", "la")
        draw_text(draw, (64, 220), config["headline"], 22, MAGENTA, "mono", "la")
        draw_text(draw, (64, 266), config["tagline"], 18, MUTED, "regular", "la")

        cx, cy = 754, 177
        for radius, color, shift in ((94, CYAN, 0), (70, MAGENTA, 0.3), (45, POWDER, 0.6)):
            start = int((phase + shift) * 360) % 360
            draw.arc((cx - radius, cy - radius, cx + radius, cy + radius), start, start + 235, fill=color, width=3)
        for node_index in range(6):
            angle = 2 * math.pi * (phase + node_index / 6)
            radius = 60 + (node_index % 2) * 22
            nx, ny = cx + math.cos(angle) * radius, cy + math.sin(angle) * radius
            draw.line((cx, cy, nx, ny), fill="#356080", width=1)
            draw.ellipse((nx - 5, ny - 5, nx + 5, ny + 5), fill=CYAN if node_index % 2 == 0 else MAGENTA)
        draw.ellipse((cx - 31, cy - 31, cx + 31, cy + 31), fill=SURFACE_2, outline=POWDER, width=2)
        draw_anchor(frame, (cx, cy), 58)
        draw.ellipse((cx - 30, cy - 30, cx + 30, cy + 30), outline=CYAN, width=2)
        scan_x = 46 + int((WIDTH - 92) * phase)
        draw.line((scan_x, 42, scan_x, height - 54), fill=mix(BG, CYAN, 0.42), width=1)
        frames.append(frame)
        durations.append(180)
    save_gif(frames, durations, ASSETS / "hero.gif", colors=160)
    return frames[0]


def chess_frame(
    base: Image.Image,
    line: dict[str, Any],
    line_index: int,
    board: dict[str, str],
    move_index: int,
    last_move: tuple[str, str] | None = None,
    moving: tuple[str, float, float] | None = None,
    final: bool = False,
) -> Image.Image:
    frame = base.copy()
    draw = ImageDraw.Draw(frame)
    draw_section_title(
        draw,
        "CHESS LAB",
        "Estrategia en movimiento",
        "Tres líneas legales · un jaque mate y dos aperturas representativas",
        42,
    )
    draw_board(
        draw,
        board,
        CHESS_ORIGIN,
        CHESS_CELL,
        last_move=last_move,
        moving=moving,
        mate=bool(final and line["mate"]),
    )
    panel(draw, (465, 171, 838, 495), MAGENTA if line["mate"] else CYAN)
    draw_text(draw, (494, 204), f"SECUENCIA 0{line_index + 1} / 03", 14, CYAN, "mono", "la")
    draw_text(draw, (494, 244), line["name"], 30, INK, "black", "la")
    accent = MAGENTA if line["mate"] and final else POWDER
    for row, value in enumerate(wrapped(line["caption"], 28)[:2]):
        draw_text(draw, (494, 289 + row * 27), value, 18, accent, "bold", "la")
    draw_text(draw, (494, 356), "NOTACIÓN", 13, MUTED, "mono", "la")
    notation_lines = wrapped(line["notation"], 31)
    for row, value in enumerate(notation_lines[:3]):
        draw_text(draw, (494, 382 + row * 24), value, 16, INK, "mono", "la")
    progress = (move_index + 1) / max(1, len(line["moves"]))
    draw.rounded_rectangle((494, 458, 806, 468), 5, fill=GRID)
    draw.rounded_rectangle((494, 458, 494 + round(312 * progress), 468), 5, fill=accent)
    return frame


def render_chess(config: dict[str, Any]) -> Image.Image:
    height = 560
    base = base_canvas(height, "CHESS")
    frames: list[Image.Image] = []
    durations: list[int] = []
    summary_frame: Image.Image | None = None
    for line_index, line in enumerate(config["chess_lines"]):
        board = initial_board()
        opening = chess_frame(base, line, line_index, board, -1)
        frames.append(opening)
        durations.append(700)
        for move_index, (source, target) in enumerate(line["moves"]):
            moving_board = deepcopy(board)
            piece = moving_board.pop(source)
            moving_board.pop(target, None)
            start = square_center(source, CHESS_ORIGIN, CHESS_CELL)
            end = square_center(target, CHESS_ORIGIN, CHESS_CELL)
            for amount in (0.35, 0.7):
                px = start[0] * (1 - amount) + end[0] * amount
                py = start[1] * (1 - amount) + end[1] * amount
                frames.append(
                    chess_frame(
                        base,
                        line,
                        line_index,
                        moving_board,
                        move_index,
                        (source, target),
                        (piece, px, py),
                    )
                )
                durations.append(90)
            apply_move(board, source, target)
            final_move = move_index == len(line["moves"]) - 1
            completed = chess_frame(
                base,
                line,
                line_index,
                board,
                move_index,
                (source, target),
                final=final_move,
            )
            frames.append(completed)
            durations.append(1150 if final_move and line["mate"] else 700 if final_move else 260)
            if final_move and line_index == 0:
                summary_frame = completed.copy()
        transition = frames[-1].copy()
        overlay = Image.new("RGBA", transition.size, rgba(BG, 80))
        transition = Image.alpha_composite(transition.convert("RGBA"), overlay).convert("RGB")
        frames.append(transition)
        durations.append(280)
    save_gif(frames, durations, ASSETS / "chess.gif", colors=160)
    return summary_frame or frames[0]


def stack_frame(
    base: Image.Image,
    config: dict[str, Any],
    snapshot: dict[str, Any],
    percentages: dict[str, float],
    page_index: int,
    offset: int = 0,
    incoming_page: int | None = None,
) -> Image.Image:
    frame = base.copy()
    draw = ImageDraw.Draw(frame)
    draw_section_title(draw, "LIVE PROFILE SYSTEM", "Stack Repository Signal", "Áreas, tecnologías y competencias", 46)
    repositories = int(
        snapshot.get("repositories_analyzed", len(snapshot.get("language_repositories", [])))
    )
    total_bytes = sum(int(value) for value in snapshot["language_bytes"].values())
    detected = sum(1 for value in snapshot["language_bytes"].values() if int(value) > 0)
    metrics = [
        (str(repositories), "REPOS ANALIZADOS"),
        (f"{total_bytes / 1_000_000:.2f} M", "BYTES LINGUIST"),
        (f"{detected} / 12", "TECNOLOGÍAS DETECTADAS"),
        (snapshot["signal_date"], "CORTE"),
    ]
    detected_order = sorted(
        (name for name in config["technologies"] if percentages[name] > 0),
        key=lambda item: (-percentages[item], item),
    )
    zero_order = sorted(
        name for name in config["technologies"] if percentages[name] <= 0
    )
    rankings = {
        name: rank + 1 for rank, name in enumerate(detected_order + zero_order)
    }
    panel(draw, (54, 192, 846, 276), POWDER, 20, 1)
    for index, (value, label) in enumerate(metrics):
        x1 = 54 + index * 198
        if index:
            draw.line((x1, 208, x1, 260), fill="#356080", width=1)
        draw_text(draw, (x1 + 99, 212), value, 23 if index != 3 else 19, INK, "black", "ma")
        draw_text(draw, (x1 + 99, 252), label, 11, CYAN if index % 2 == 0 else MAGENTA, "mono", "ms")

    areas = config["areas"]
    draw_text(draw, (54, 304), "ÁREAS DE APLICACIÓN", 13, CYAN, "mono", "la")
    area_width = 187
    for index, value in enumerate(areas):
        x = 54 + index * (area_width + 11)
        accent = CYAN if index % 2 == 0 else MAGENTA
        panel(draw, (x, 326, x + area_width, 382), accent, 17, 1)
        draw_text(draw, (x + 18, 344), f"0{index + 1}", 11, accent, "mono", "la")
        draw_text(draw, (x + area_width / 2, 361), value, 17, POWDER, "bold", "mm")
        node_x = x + area_width / 2
        draw.line((node_x, 382, node_x, 404), fill="#3B6F91", width=1)
        draw.ellipse((node_x - 4, 398, node_x + 4, 406), fill=accent)
    draw.line((88, 404, 812, 404), fill="#3B6F91", width=2)
    draw.ellipse((446, 399, 456, 409), fill=CYAN)

    draw_text(draw, (54, 429), "TECNOLOGÍAS", 14, CYAN, "mono", "la")
    draw_text(draw, (846, 429), f"ESCENA 0{page_index + 1} / 02  ·  6 DE 12", 13, MAGENTA, "mono", "ra")

    pages = [config["technologies"][6:], config["technologies"][:6]]
    repo_counts = snapshot.get("language_repo_counts", {})

    def draw_page(page: int, shift: int) -> None:
        for index, technology in enumerate(pages[page]):
            col, row = index % 2, index // 2
            x = 54 + col * 404 + shift
            y = 452 + row * 146
            if x > WIDTH or x + 376 < 0:
                continue
            accent = TECH_COLORS[technology]
            shadow = (x + 7, y + 8, x + 395, y + 138)
            draw.rounded_rectangle(shadow, 23, fill="#050810")
            panel(draw, (x, y, x + 388, y + 130), accent, 22, 2)
            draw_logo(frame, (x + 57, y + 65), technology, 58)
            draw_text(draw, (x + 106, y + 24), technology, 22, INK, "black", "la")
            draw_text(draw, (x + 360, y + 24), f"#{rankings[technology]:02d}", 14, accent, "mono", "ra")
            value = percentages[technology]
            byte_count = int(snapshot["language_bytes"].get(technology, 0))
            draw_text(draw, (x + 106, y + 55), f"{value:.1f}%", 29, accent, "black", "la")
            bytes_label = f"{byte_count / 1_000_000:.2f} M bytes" if byte_count >= 1_000_000 else f"{byte_count / 1000:.1f} K bytes"
            draw_text(draw, (x + 360, y + 67), bytes_label, 13, MUTED, "mono", "rs")
            repo_count = int(repo_counts.get(technology, 0))
            repo_word = "REPO" if repo_count == 1 else "REPOS"
            state = f"SEÑAL DETECTADA · {repo_count} {repo_word}" if value > 0 else "DECLARADA · SIN BYTES DETECTADOS"
            draw_text(draw, (x + 106, y + 103), state, 13, POWDER if value > 0 else MAGENTA, "mono", "ls")

    draw_page(page_index, offset)
    if incoming_page is not None:
        incoming_shift = offset + (WIDTH if offset <= 0 else -WIDTH)
        draw_page(incoming_page, incoming_shift)

    panel(draw, (54, 904, 846, 1116), MAGENTA, 24, 1)
    draw_text(draw, (78, 934), "COMPETENCIAS CONECTADAS", 14, CYAN, "mono", "la")
    descriptors = ["INTEGRACIÓN", "MODELADO", "CALIDAD", "PERSISTENCIA", "PERCEPCIÓN", "TRAZABILIDAD"]
    for index, (value, descriptor) in enumerate(zip(config["competencies"], descriptors)):
        col, row = index % 2, index // 2
        x, y = 78 + col * 382, 962 + row * 48
        accent = CYAN if index % 2 == 0 else MAGENTA
        draw.rounded_rectangle((x, y, x + 358, y + 40), 13, fill=SURFACE_2, outline="#356080", width=1)
        draw.ellipse((x + 14, y + 14, x + 26, y + 26), fill=accent)
        draw_text(draw, (x + 38, y + 20), value, 15, INK, "bold", "lm")
        draw_text(draw, (x + 340, y + 20), descriptor, 11, MUTED, "mono", "rm")
    draw_text(draw, (54, 1150), "GitHub Linguist · repositorios públicos originales · la señal no equivale a nivel de dominio", 14, MUTED, "regular", "la")
    draw_text(draw, (846, 1180), "GENERADO LOCALMENTE · SIN DEPENDENCIAS DE CARGA", 12, POWDER, "mono", "rs")
    return frame


def render_stack(
    config: dict[str, Any],
    snapshot: dict[str, Any],
) -> Image.Image:
    height = 1240
    base = base_canvas(height, "STACK")
    base.info["signal_date"] = snapshot["signal_date"]
    percentages = normalized_percentages(snapshot, config["technologies"])
    frames: list[Image.Image] = []
    durations: list[int] = []
    page_a = stack_frame(base, config, snapshot, percentages, 0)
    page_b = stack_frame(base, config, snapshot, percentages, 1)
    frames.append(page_a)
    durations.append(2500)
    for index in range(1, 8):
        frames.append(stack_frame(base, config, snapshot, percentages, 0, -round(WIDTH * index / 8), 1))
        durations.append(75)
    frames.append(page_b)
    durations.append(2500)
    for index in range(1, 8):
        frames.append(stack_frame(base, config, snapshot, percentages, 1, -round(WIDTH * index / 8), 0))
        durations.append(75)
    save_gif(frames, durations, ASSETS / "stack.gif", colors=192)
    return page_a


def project_card(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    project: dict[str, Any],
    active: bool,
) -> None:
    accent = TECH_COLORS.get(project.get("language"), CYAN)
    x1, y1, x2, y2 = box
    panel(draw, box, accent, 22, 3 if active else 2)
    draw.rounded_rectangle((x1 + 24, y1 + 24, x1 + 76, y1 + 76), 15, fill=mix(SURFACE, accent, 0.50), outline=accent, width=2)
    draw_text(draw, (x1 + 50, y1 + 51), str(project["name"])[0].upper(), 23, INK, "black", "mm")
    title = project["name"]
    title_size = 22 if len(title) < 22 else 18
    draw_text(draw, (x1 + 92, y1 + 27), title, title_size, INK, "black", "la")
    draw_text(draw, (x1 + 92, y1 + 60), f"{project.get('language') or 'Multi-stack'}  ·  ★ {project.get('stars', 0)}", 14, accent, "mono", "la")
    for row, value in enumerate(wrapped(project["description"], 42)[:2]):
        draw_text(draw, (x1 + 24, y1 + 105 + row * 23), value, 16, MUTED, "regular", "la")
    updated = str(project.get("updated_at") or "")[:10]
    draw_text(draw, (x2 - 24, y2 - 18), f"UPDATE · {updated}", 11, POWDER, "mono", "rs")


def render_projects(config: dict[str, Any], snapshot: dict[str, Any]) -> Image.Image:
    height = 850
    base = base_canvas(height, "PROJECTS")
    featured_limit = int(config.get("featured_limit", 6))
    projects = snapshot["projects"][:featured_limit]
    frames: list[Image.Image] = []
    durations: list[int] = []
    for active_row in range(3):
        frame = base.copy()
        draw = ImageDraw.Draw(frame)
        draw_section_title(
            draw,
            "CURATED AUTOMATICALLY",
            "Proyectos destacados",
            "Selección equilibrada por actividad, profundidad y valor profesional",
            44,
        )
        for index, project in enumerate(projects):
            col, row = index % 2, index // 2
            x = 62 + col * 409
            y = 186 + row * 190
            project_card(draw, (x, y, x + 376, y + 166), project, row == active_row)
        draw_text(draw, (62, 775), "METADATA LOCAL · ENLACES REALES DEBAJO DE LA IMAGEN", 13, CYAN, "mono", "la")
        frames.append(frame)
        durations.append(1500)
    save_gif(frames, durations, ASSETS / "projects.gif", colors=176)
    return frames[0]


def render_social(config: dict[str, Any]) -> Image.Image:
    height = 420
    base = base_canvas(height, "SOCIAL")
    frames: list[Image.Image] = []
    durations: list[int] = []
    channels = [
        ("GitHub", f"github.com/{config['username']}", CYAN),
        ("WhatsApp", config["whatsapp_display"], GREEN),
        ("Ubicación", config["location"], MAGENTA),
    ]
    for index in range(24):
        frame = base.copy()
        draw = ImageDraw.Draw(frame)
        draw_section_title(
            draw,
            "OPEN CHANNEL",
            config["social_title"],
            config["social_subtitle"],
            42,
        )
        card_y = 198
        for channel_index, (label, value, accent) in enumerate(channels):
            x = 62 + channel_index * 269
            panel(draw, (x, card_y, x + 240, card_y + 126), accent, 22, 2)
            draw.rounded_rectangle((x + 20, card_y + 27, x + 74, card_y + 81), 16, fill=mix(SURFACE, accent, 0.50), outline=accent, width=2)
            draw_social_icon(frame, (x + 47, card_y + 54), label, 30)
            draw_text(draw, (x + 91, card_y + 32), label, 16, accent, "bold", "la")
            for row, line in enumerate(wrapped(value, 22)[:2]):
                draw_text(draw, (x + 91, card_y + 61 + row * 21), line, 14, POWDER, "regular", "la")
        progress = index / 24
        line_y = 347
        draw.line((78, line_y, 822, line_y), fill="#356080", width=2)
        tracer_x = 78 + progress * 744
        draw.ellipse((tracer_x - 7, line_y - 7, tracer_x + 7, line_y + 7), fill=CYAN, outline=INK, width=1)
        frames.append(frame)
        durations.append(170)
    save_gif(frames, durations, ASSETS / "social.gif", colors=160)
    return frames[0]


def svg_open(height: int, code: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" role="img">',
        f"<title>Luics415 · {html.escape(code)}</title>",
        "<defs>",
        f'<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#06385C"/><stop offset=".56" stop-color="{BG}"/><stop offset="1" stop-color="#16031F"/></linearGradient>',
        f'<linearGradient id="signal" x1="0" y1="0" x2="1" y2="0"><stop stop-color="{CYAN}"/><stop offset="1" stop-color="{MAGENTA}"/></linearGradient>',
        f'<radialGradient id="glow-cyan"><stop stop-color="{CYAN}" stop-opacity=".31"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></radialGradient>',
        f'<radialGradient id="glow-magenta"><stop stop-color="{MAGENTA}" stop-opacity=".27"/><stop offset="1" stop-color="{MAGENTA}" stop-opacity="0"/></radialGradient>',
        f'<radialGradient id="glow-wine"><stop stop-color="{WINE}" stop-opacity=".30"/><stop offset="1" stop-color="{WINE}" stop-opacity="0"/></radialGradient>',
        f'<pattern id="grid" width="60" height="60" patternUnits="userSpaceOnUse"><path d="M60 0H0V60" fill="none" stroke="{GRID}" stroke-width="1"/></pattern>',
        "</defs>",
        f'<rect width="{WIDTH}" height="{height}" fill="url(#bg)"/>',
        f'<ellipse cx="110" cy="90" rx="320" ry="250" fill="url(#glow-cyan)"/>',
        f'<ellipse cx="800" cy="90" rx="280" ry="240" fill="url(#glow-magenta)"/>',
        f'<ellipse cx="790" cy="{height - 40}" rx="340" ry="280" fill="url(#glow-wine)"/>',
        f'<rect width="{WIDTH}" height="{height}" fill="url(#grid)" opacity=".82"/>',
        f'<rect x="18" y="18" width="{WIDTH - 36}" height="{height - 36}" rx="26" fill="none" stroke="#4A9BC7" stroke-width="2"/>',
    ]


def svg_text(
    x: float,
    y: float,
    value: str,
    size: int,
    fill: str = INK,
    weight: int = 400,
    anchor: str = "start",
    mono: bool = False,
) -> str:
    family = "ui-monospace,Consolas,monospace" if mono else "Segoe UI,Arial,sans-serif"
    return (
        f'<text x="{x}" y="{y}" fill="{fill}" font-family="{family}" '
        f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}">'
        f"{html.escape(value)}</text>"
    )


def svg_panel(x: int, y: int, width: int, height: int, accent: str = CYAN) -> str:
    return (
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="22" '
        f'fill="{mix_hex(SURFACE, accent, 0.11)}" stroke="{accent}" stroke-opacity=".90"/>'
    )


def write_hero_svg(config: dict[str, Any]) -> None:
    lines = svg_open(360, "Hero estático")
    lines += [
        svg_text(62, 78, "SOFTWARE ENGINEERING // PROFILE", 15, CYAN, 600, mono=True),
        svg_text(62, 142, config["name"], 44, INK, 800),
        svg_text(64, 198, config["role"], 27, POWDER, 700),
        svg_text(64, 238, config["headline"], 22, MAGENTA, 600, mono=True),
        svg_text(64, 282, config["tagline"], 18, MUTED),
        f'<circle cx="754" cy="177" r="92" fill="none" stroke="{CYAN}" stroke-width="3" stroke-dasharray="330 250"/>',
        f'<circle cx="754" cy="177" r="66" fill="none" stroke="{MAGENTA}" stroke-width="3" stroke-dasharray="220 200"/>',
        f'<circle cx="754" cy="177" r="31" fill="{SURFACE_2}" stroke="{POWDER}" stroke-width="2"/>',
        svg_anchor(725, 148, 58),
        f'<circle cx="754" cy="177" r="30" fill="none" stroke="{CYAN}" stroke-width="2"/>',
        svg_text(46, 326, "LUICS415 // HERO", 13, MUTED, 400, mono=True),
        "</svg>",
    ]
    (ASSETS / "hero.svg").write_text("\n".join(lines) + "\n", encoding="utf-8")


def board_after(line: dict[str, Any]) -> dict[str, str]:
    board = initial_board()
    for source, target in line["moves"]:
        apply_move(board, source, target)
    return board


def write_chess_svg(config: dict[str, Any]) -> None:
    height = 560
    lines = svg_open(height, "Tres líneas de ajedrez")
    lines += [
        svg_text(60, 72, "CHESS LAB", 15, CYAN, 600, mono=True),
        svg_text(60, 120, "Estrategia en movimiento", 42, INK, 800),
        svg_text(60, 154, "Mate del Pastor · Apertura Bird · Defensa Caro-Kann", 19, MUTED),
    ]
    mini_size = 240
    cell = 28
    for line_index, line in enumerate(config["chess_lines"]):
        x, y = 60 + line_index * 271, 198
        board = board_after(line)
        board_origin = (x + 8, y + 8)
        lines.append(svg_panel(x, y, mini_size, 302, MAGENTA if line["mate"] else CYAN))
        for rank in range(8):
            for file_index in range(8):
                fill = POWDER if (rank + file_index) % 2 == 0 else "#356080"
                lines.append(
                    f'<rect x="{board_origin[0] + file_index * cell}" y="{board_origin[1] + rank * cell}" width="{cell}" height="{cell}" fill="{fill}"/>'
                )
        for square, piece in board.items():
            cx, cy = square_center(square, board_origin, cell)
            fill = "#F8FBFF" if piece.isupper() else "#09101A"
            lines.append(svg_text(cx, cy + 8, PIECE_GLYPHS[piece], 25, fill, 400, "middle"))
        lines.append(svg_text(x, y + 267, line["name"], 20, INK, 800))
        caption = "4.Qxf7# · Jaque mate" if line["mate"] else "Línea representativa"
        lines.append(svg_text(x, y + 291, caption, 14, MAGENTA if line["mate"] else POWDER, 600))
    lines += [
        svg_text(46, 526, "LUICS415 // CHESS", 13, MUTED, 400, mono=True),
        "</svg>",
    ]
    (ASSETS / "chess.svg").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_stack_svg(
    config: dict[str, Any],
    snapshot: dict[str, Any],
) -> None:
    height = 1390
    percentages = normalized_percentages(snapshot, config["technologies"])
    lines = svg_open(height, "Stack Repository Signal")
    lines += [
        svg_text(60, 72, "LIVE PROFILE SYSTEM", 15, CYAN, 600, mono=True),
        svg_text(60, 124, "Stack Repository Signal", 46, INK, 800),
        svg_text(60, 160, "Áreas, tecnologías y competencias", 20, MUTED),
    ]
    total_bytes = sum(int(value) for value in snapshot["language_bytes"].values())
    detected = sum(1 for value in snapshot["language_bytes"].values() if int(value) > 0)
    metrics = [
        (
            str(snapshot.get("repositories_analyzed", len(snapshot.get("language_repositories", [])))),
            "REPOS ANALIZADOS",
        ),
        (f"{total_bytes / 1_000_000:.2f} M", "BYTES LINGUIST"),
        (f"{detected} / 12", "TECNOLOGÍAS"),
        (snapshot["signal_date"], "CORTE"),
    ]
    lines.append(svg_panel(54, 210, 792, 82, POWDER))
    for index, (value, label) in enumerate(metrics):
        x = 153 + index * 198
        lines.append(svg_text(x, 246, value, 21 if index != 3 else 17, INK, 800, "middle"))
        lines.append(svg_text(x, 274, label, 11, CYAN if index % 2 == 0 else MAGENTA, 600, "middle", True))
    lines.append(svg_text(54, 322, "ÁREAS DE APLICACIÓN", 13, CYAN, 600, mono=True))
    for index, area in enumerate(config["areas"]):
        x = 54 + index * 198
        lines.append(svg_panel(x, 338, 187, 52, CYAN if index % 2 == 0 else MAGENTA))
        lines.append(svg_text(x + 94, 371, area, 17, POWDER, 700, "middle"))
    repo_counts = snapshot.get("language_repo_counts", {})

    def append_technology_card(technology: str, x: int, y: int) -> None:
        accent = TECH_COLORS[technology]
        lines.append(svg_panel(x, y, 388, 98, accent))
        lines.append(f'<rect x="{x + 16}" y="{y + 14}" width="70" height="70" rx="17" fill="#F7FAFC" stroke="{accent}"/>')
        lines.append(svg_brand_icon(technology, x + 25, y + 23, 52))
        lines.append(svg_text(x + 102, y + 32, technology, 20, INK, 800))
        lines.append(svg_text(x + 102, y + 65, f"{percentages[technology]:.1f}%", 24, accent, 800))
        byte_count = int(snapshot["language_bytes"].get(technology, 0))
        lines.append(svg_text(x + 362, y + 63, f"{byte_count:,} bytes", 11, MUTED, 500, "end", True))
        repo_count = int(repo_counts.get(technology, 0))
        repo_word = "REPO" if repo_count == 1 else "REPOS"
        state = f"SEÑAL DETECTADA · {repo_count} {repo_word}" if percentages[technology] > 0 else "DECLARADA · SIN BYTES DETECTADOS"
        lines.append(svg_text(x + 102, y + 84, state, 10, POWDER if percentages[technology] > 0 else MAGENTA, 600, mono=True))

    banks = [config["technologies"][6:], config["technologies"][:6]]
    bank_specs = [
        ("BANCO 01 · SEÑAL PRINCIPAL", 424, 442, CYAN),
        ("BANCO 02 · COMPETENCIAS DECLARADAS", 796, 814, MAGENTA),
    ]
    for bank, (label, label_y, cards_y, label_color) in zip(banks, bank_specs):
        lines.append(svg_text(54, label_y, label, 13, label_color, 600, mono=True))
        for index, technology in enumerate(bank):
            col, row = index % 2, index // 2
            append_technology_card(technology, 54 + col * 404, cards_y + row * 112)

    competence_pairs = [
        (("API REST", "INTEGRACIÓN"), ("POO", "MODELADO")),
        (("Código limpio", "CALIDAD"), ("Bases de datos", "PERSISTENCIA")),
        (("Visión por computadora", "PERCEPCIÓN"), ("Documentación", "TRAZABILIDAD")),
    ]
    lines += [
        svg_panel(54, 1158, 792, 162, MAGENTA),
        svg_text(78, 1188, "COMPETENCIAS CONECTADAS", 14, CYAN, 600, mono=True),
    ]
    for row, pair in enumerate(competence_pairs):
        for col, (competence, descriptor) in enumerate(pair):
            x, y = 78 + col * 382, 1222 + row * 34
            lines.append(svg_text(x, y, competence, 15, INK, 700))
            lines.append(svg_text(x + 330, y, descriptor, 11, MUTED, 500, "end", True))
    lines += [
        svg_text(54, 1350, "GitHub Linguist · repositorios públicos originales · la señal no equivale a nivel de dominio", 14, MUTED),
        "</svg>",
    ]
    (ASSETS / "stack.svg").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_projects_svg(config: dict[str, Any], snapshot: dict[str, Any]) -> None:
    height = 850
    lines = svg_open(height, "Proyectos destacados")
    lines += [
        svg_text(60, 72, "CURATED AUTOMATICALLY", 15, CYAN, 600, mono=True),
        svg_text(60, 122, "Proyectos destacados", 44, INK, 800),
        svg_text(60, 158, "Actividad, profundidad y valor profesional", 19, MUTED),
    ]
    featured_limit = int(config.get("featured_limit", 6))
    for index, project in enumerate(snapshot["projects"][:featured_limit]):
        col, row = index % 2, index // 2
        x, y = 60 + col * 409, 190 + row * 186
        accent = TECH_COLORS.get(project.get("language"), CYAN)
        lines.append(svg_panel(x, y, 376, 162, accent))
        lines.append(f'<rect x="{x + 22}" y="{y + 22}" width="52" height="52" rx="15" fill="{SURFACE_2}" stroke="{accent}"/>')
        lines.append(svg_text(x + 48, y + 56, project["name"][0].upper(), 22, INK, 800, "middle"))
        title_size = 21 if len(project["name"]) < 22 else 17
        lines.append(svg_text(x + 90, y + 42, project["name"], title_size, INK, 800))
        lines.append(svg_text(x + 90, y + 68, f"{project.get('language') or 'Multi-stack'} · ★ {project.get('stars', 0)}", 13, accent, 600, mono=True))
        for row_index, value in enumerate(wrapped(project["description"], 42)[:2]):
            lines.append(svg_text(x + 22, y + 105 + row_index * 21, value, 15, MUTED))
        lines.append(svg_text(x + 354, y + 145, str(project.get("updated_at") or "")[:10], 11, POWDER, 500, "end", True))
    lines += [
        svg_text(60, 780, "Los enlaces reales aparecen debajo de esta imagen en el README.", 14, MUTED),
        svg_text(46, 816, "LUICS415 // PROJECTS", 13, MUTED, 400, mono=True),
        "</svg>",
    ]
    (ASSETS / "projects.svg").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_social_svg(config: dict[str, Any]) -> None:
    height = 420
    lines = svg_open(height, "Contacto")
    lines += [
        svg_text(60, 72, "OPEN CHANNEL", 15, CYAN, 600, mono=True),
        svg_text(60, 120, config["social_title"], 42, INK, 800),
        svg_text(60, 156, config["social_subtitle"], 19, MUTED),
    ]
    channels = [
        ("GitHub", f"github.com/{config['username']}", CYAN),
        ("WhatsApp", config["whatsapp_display"], GREEN),
        ("Ubicación", config["location"], MAGENTA),
    ]
    for index, (label, value, accent) in enumerate(channels):
        x, y = 60 + index * 270, 202
        lines.append(svg_panel(x, y, 240, 126, accent))
        lines.append(f'<rect x="{x + 20}" y="{y + 28}" width="54" height="54" rx="16" fill="{SURFACE_2}" stroke="{accent}"/>')
        lines.append(svg_social_icon(label, x + 32, y + 39, 30))
        lines.append(svg_text(x + 90, y + 46, label, 16, accent, 700))
        lines.append(svg_text(x + 90, y + 75, value, 13, POWDER, 500))
    lines += [
        '<line x1="78" y1="351" x2="822" y2="351" stroke="#356080" stroke-width="2"/>',
        f'<circle cx="450" cy="351" r="7" fill="{CYAN}" stroke="{INK}"/>',
        svg_text(46, 386, "LUICS415 // SOCIAL", 13, MUTED, 400, mono=True),
        "</svg>",
    ]
    (ASSETS / "social.svg").write_text("\n".join(lines) + "\n", encoding="utf-8")


def replace_marked_block(source: str, marker: str, content: str) -> str:
    start = f"<!-- {marker}:START -->"
    end = f"<!-- {marker}:END -->"
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    replacement = f"{start}\n{content.rstrip()}\n{end}"
    if not pattern.search(source):
        return source
    return pattern.sub(lambda _: replacement, source)


def update_readme(
    config: dict[str, Any],
    snapshot: dict[str, Any],
) -> None:
    if not README.exists():
        return
    percentages = normalized_percentages(snapshot, config["technologies"])
    rows = "\n".join(
        f"| {technology} | {percentages[technology]:.1f}% |"
        for technology in config["technologies"]
    )
    stack_block = f"""<details>
<summary>Datos y metodología de la señal</summary>

| Tecnología | Señal de repositorios |
| --- | ---: |
{rows}

Calculado con bytes informados por GitHub Linguist sobre repositorios públicos
originales, sin forks ni copias conocidas. **No representa nivel de dominio
personal.** Catálogo: {snapshot.get("repositories_fetched", "—")} repositorios
públicos encontrados y {snapshot.get("repositories_analyzed", "—")} analizados
para la señal. Corte: {snapshot["signal_date"]}.
</details>"""

    project_lines = "\n".join(
        f"- [{project['name']}]({project['url']}) — {project['description']}"
        for project in snapshot["projects"][: int(config.get("featured_limit", 6))]
    )
    project_block = (
        f"{project_lines}\n\n"
        "_La selección visual se regenera con metadatos públicos; los enlaces "
        "anteriores permanecen accesibles y clicables._"
    )
    all_projects = snapshot.get("all_projects", snapshot["projects"])
    all_project_lines = "\n".join(
        f"- [{project['name']}]({project['url']}) — {project['description']}"
        for project in all_projects
    )
    all_projects_block = (
        f"<details>\n<summary>Ver los {len(all_projects)} proyectos públicos elegibles</summary>\n\n"
        f"{all_project_lines}\n\n"
        "_Esta lista se regenera automáticamente; excluye el repositorio del perfil, "
        "forks, repositorios archivados y copias configuradas._\n</details>"
    )
    source = README.read_text(encoding="utf-8")
    source = replace_marked_block(source, "STACK-DATA", stack_block)
    source = replace_marked_block(source, "PROJECT-LINKS", project_block)
    source = replace_marked_block(source, "ALL-PROJECTS", all_projects_block)
    README.write_text(source, encoding="utf-8")


def build_preview(statics: list[tuple[str, Image.Image]]) -> None:
    preview_width = 540
    gap = 18
    resized: list[tuple[str, Image.Image]] = []
    total_height = 36
    for label, image in statics:
        height = round(image.height * preview_width / image.width)
        smaller = image.resize((preview_width, height), Image.Resampling.LANCZOS)
        resized.append((label, smaller))
        total_height += height + gap + 28
    preview = Image.new("RGB", (preview_width + 36, total_height), "#04070D")
    draw = ImageDraw.Draw(preview)
    y = 18
    for label, image in resized:
        draw_text(draw, (18, y), label.upper(), 15, CYAN, "mono", "la")
        y += 24
        preview.paste(image, (18, y))
        y += image.height + gap
    preview.save(ASSETS / "preview.png", optimize=True)


def write_svg_assets(
    config: dict[str, Any],
    snapshot: dict[str, Any],
) -> None:
    write_hero_svg(config)
    write_chess_svg(config)
    write_stack_svg(config, snapshot)
    write_projects_svg(config, snapshot)
    write_social_svg(config)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use the committed snapshot instead of contacting GitHub.",
    )
    parser.add_argument(
        "--strict-refresh",
        action="store_true",
        help="Fail instead of falling back to the snapshot when GitHub refresh fails.",
    )
    args = parser.parse_args()
    ASSETS.mkdir(parents=True, exist_ok=True)
    config = load_json(DATA / "profile.json")
    snapshot_path = DATA / "profile-snapshot.json"
    if args.offline:
        snapshot = load_json(snapshot_path)
        print("Using committed profile snapshot.")
    else:
        try:
            snapshot = fetch_snapshot(config)
            if len(snapshot.get("projects", [])) < 6:
                raise RuntimeError("GitHub returned fewer than six usable projects")
            write_json(snapshot_path, snapshot)
            print(
                f"Fetched {snapshot.get('repositories_fetched', '?')} public repositories; "
                f"analyzed {snapshot.get('repositories_analyzed', '?')} for {config['username']}."
            )
        except (OSError, urllib.error.URLError, urllib.error.HTTPError, RuntimeError) as error:
            if args.strict_refresh:
                raise RuntimeError(f"Strict GitHub refresh failed: {error}") from error
            print(f"GitHub refresh unavailable ({error}); using committed snapshot.")
            snapshot = load_json(snapshot_path)

    hero = render_hero(config)
    chess = render_chess(config)
    stack = render_stack(config, snapshot)
    projects = render_projects(config, snapshot)
    social = render_social(config)
    write_svg_assets(config, snapshot)
    update_readme(config, snapshot)
    build_preview(
        [
            ("Hero", hero),
            ("Chess", chess),
            ("Stack Repository Signal", stack),
            ("Projects", projects),
            ("Social", social),
        ]
    )
    print("Generated hero, chess, stack, projects and social assets.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
