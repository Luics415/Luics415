#!/usr/bin/env python3
"""Validate generated profile assets and README integration."""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

from generate_profile_assets import CHESS_CELL, CHESS_ORIGIN, apply_move, initial_board


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
EXPECTED = {
    "hero": (900, 360),
    "chess": (900, 560),
    "stack": (900, 1240),
    "projects": (900, 850),
    "social": (900, 420),
}
SVG_EXPECTED_HEIGHTS = {
    "hero": 360,
    "chess": 560,
    "stack": 1390,
    "projects": 850,
    "social": 420,
}


def fail(message: str) -> None:
    raise AssertionError(message)


def validate_gifs() -> tuple[int, list[str]]:
    total_size = 0
    report: list[str] = []
    for name, expected_size in EXPECTED.items():
        path = ASSETS / f"{name}.gif"
        if not path.exists():
            fail(f"Missing {path}")
        file_size = path.stat().st_size
        total_size += file_size
        if file_size > 5 * 1024 * 1024:
            fail(f"{path.name} exceeds the 5 MiB per-module budget")
        with Image.open(path) as image:
            if image.size != expected_size:
                fail(f"{path.name}: expected {expected_size}, got {image.size}")
            if getattr(image, "n_frames", 1) < 2:
                fail(f"{path.name} is not animated")
            if image.info.get("loop") != 0:
                fail(f"{path.name} does not loop continuously")
            duration = 0
            for index in range(image.n_frames):
                image.seek(index)
                duration += int(image.info.get("duration", 0))
            report.append(
                f"{path.name}: {image.n_frames} frames, "
                f"{duration / 1000:.1f}s, {file_size / 1024:.0f} KiB"
            )
    if total_size > 12 * 1024 * 1024:
        fail("The five GIFs exceed the 12 MiB total performance budget")
    return total_size, report


def validate_svgs() -> None:
    for name, expected_height in SVG_EXPECTED_HEIGHTS.items():
        path = ASSETS / f"{name}.svg"
        if not path.exists():
            fail(f"Missing {path}")
        root = ET.parse(path).getroot()
        if root.attrib.get("width") != "900":
            fail(f"{path.name}: width is not 900")
        if root.attrib.get("height") != str(expected_height):
            fail(f"{path.name}: unexpected height")
        if path.stat().st_size > 500 * 1024:
            fail(f"{path.name} exceeds 500 KiB")
        if 'fill="(' in path.read_text(encoding="utf-8"):
            fail(f"{path.name} contains an invalid tuple color")


def validate_chess(config: dict) -> None:
    ox, oy = CHESS_ORIGIN
    wrapper = (ox - 8, oy - 8, ox + CHESS_CELL * 8 + 8, oy + CHESS_CELL * 8 + 8)
    if wrapper[0] < 46 or wrapper[2] > 430 or wrapper[3] > 500:
        fail(f"Chess board wrapper escapes its safe area: {wrapper}")
    if CHESS_CELL * 0.44 >= CHESS_CELL / 2:
        fail("Checkmate halo can escape its chess square")
    for line in config["chess_lines"]:
        board = initial_board()
        expected_white = True
        for source, target in line["moves"]:
            piece = board.get(source)
            if piece is None:
                fail(f"{line['name']}: no piece on {source}")
            if piece.isupper() != expected_white:
                fail(f"{line['name']}: wrong side to move at {source}-{target}")
            apply_move(board, source, target)
            expected_white = not expected_white
    pastor = config["chess_lines"][0]
    if pastor["notation"] != "1.e4 e5 2.Bc4 Nc6 3.Qh5 Nf6?? 4.Qxf7#":
        fail("Mate del Pastor notation changed unexpectedly")
    if not pastor["mate"]:
        fail("Mate del Pastor must be identified as mate")
    if any(line["mate"] for line in config["chess_lines"][1:]):
        fail("Bird and Caro-Kann must not be labeled as mate")


def validate_snapshot(config: dict, snapshot: dict) -> None:
    technologies = config["technologies"]
    if len(technologies) != 12 or len(set(technologies)) != 12:
        fail("Exactly 12 unique technologies are required")
    if set(snapshot["language_bytes"]) != set(technologies):
        fail("Snapshot technologies do not match configuration")
    if sum(int(value) for value in snapshot["language_bytes"].values()) <= 0:
        fail("Language snapshot is empty")
    fetched = int(snapshot.get("repositories_fetched", 0))
    analyzed = int(snapshot.get("repositories_analyzed", 0))
    if fetched <= 0 or analyzed <= 0 or analyzed > fetched:
        fail("Repository inventory counts are missing or inconsistent")
    if len(snapshot["projects"]) < 6:
        fail("At least six projects are required")
    featured_limit = int(config.get("featured_limit", 6))
    if len(snapshot["projects"]) != featured_limit:
        fail("Snapshot featured project count does not match featured_limit")
    featured_names = {project["name"] for project in snapshot["projects"]}
    for required_name in config.get("featured_required", []):
        if required_name not in featured_names:
            fail(f"Required featured project is missing: {required_name}")
    if "all_projects" in snapshot and len(snapshot["all_projects"]) < len(snapshot["projects"]):
        fail("Complete project inventory is shorter than the featured selection")
    expected_subtitle = "La lógica es el ancla; cada proyecto encuentra su dirección."
    if config.get("social_subtitle") != expected_subtitle:
        fail("Social subtitle changed from the user's requested copy")
    if "construyamos algo útil" in config.get("social_title", "").casefold():
        fail("Old social title is still configured")
    if "código anclado, ideas con rumbo" in config.get("social_title", "").casefold():
        fail("Rejected social title is still configured")
    counts = snapshot.get("language_repo_counts")
    if not isinstance(counts, dict) or set(counts) != set(technologies):
        fail("Snapshot repository counts do not match the 12 technologies")
    scholarship = next(
        (project for project in snapshot["projects"] if project["name"] == "sistema-becas"),
        None,
    )
    if scholarship:
        description = scholarship["description"].casefold()
        if "postgres" in description or "laravel" in description:
            fail("sistema-becas still contains the old incorrect description")
        if "mysql" not in description:
            fail("sistema-becas description must mention MySQL/MariaDB")


def validate_readme() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    lowered = readme.casefold()
    if "gitskins.com" in lowered:
        fail("README still depends on GitSkins")
    if "mailto:" in lowered or "@gmail" in lowered:
        fail("README contains an email address")
    if "construyamos algo útil" in lowered:
        fail("README still contains the rejected social phrase")
    if "código anclado, ideas con rumbo" in lowered:
        fail("README still contains the rejected social title")
    required = [
        "Stack Repository Signal",
        "Áreas, tecnologías y competencias",
        "https://wa.me/525561525238",
        "<!-- STACK-DATA:START -->",
        "<!-- STACK-DATA:END -->",
        "<!-- PROJECT-LINKS:START -->",
        "<!-- PROJECT-LINKS:END -->",
        "<!-- ALL-PROJECTS:START -->",
        "<!-- ALL-PROJECTS:END -->",
    ]
    for value in required:
        if value.casefold() not in lowered:
            fail(f"README is missing: {value}")
    for name in EXPECTED:
        if f"./assets/{name}.gif" not in readme:
            fail(f"README does not reference {name}.gif")
        if f"./assets/{name}.svg" not in readme:
            fail(f"README does not reference {name}.svg")


def validate_official_icons(config: dict) -> None:
    icon_dir = ASSETS / "icons"
    if not (icon_dir / "DEVICON_LICENSE").exists():
        fail("Missing the vendored Devicon license")
    stems = {
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
    if set(stems) != set(config["technologies"]):
        fail("Official icon map does not match configured technologies")
    for technology, stem in stems.items():
        for extension in ("svg", "png"):
            path = icon_dir / f"{stem}.{extension}"
            if not path.exists() or path.stat().st_size == 0:
                fail(f"Missing official {technology} logo: {path.name}")
        with Image.open(icon_dir / f"{stem}.png") as icon:
            if icon.size != (256, 256):
                fail(f"{stem}.png must be 256x256")
    generator = (ROOT / "scripts" / "generate_profile_assets.py").read_text(encoding="utf-8")
    if "def initials(" in generator or "elif technology" in generator:
        fail("Custom-drawn technology logo fallback remains in the generator")
    if "load_brand_icon" not in generator or "svg_brand_icon" not in generator:
        fail("Generated assets are not wired to the official logo files")


def validate_interface_icons() -> None:
    social_dir = ASSETS / "icons" / "social"
    for name in ("github", "whatsapp", "location"):
        for extension in ("svg", "png"):
            path = social_dir / f"{name}.{extension}"
            if not path.exists() or path.stat().st_size == 0:
                fail(f"Missing local social icon: {path.name}")
        with Image.open(social_dir / f"{name}.png") as icon:
            if icon.size != (256, 256):
                fail(f"{name}.png must be 256x256")
    if not (social_dir / "BOOTSTRAP_ICONS_LICENSE").exists():
        fail("Missing Bootstrap Icons license")
    anchor = ASSETS / "brand" / "anchor.png"
    if not anchor.exists():
        fail("Missing personal Hero anchor")
    with Image.open(anchor) as icon:
        if icon.size != (512, 512):
            fail("Hero anchor must be 512x512")
    hero_svg = (ASSETS / "hero.svg").read_text(encoding="utf-8")
    social_svg = (ASSETS / "social.svg").read_text(encoding="utf-8")
    if "data:image/png;base64," not in hero_svg:
        fail("Hero SVG does not embed the personal anchor")
    if ">LR<" in hero_svg:
        fail("Hero SVG still contains the old LR monogram")
    required_icons = (
        "M8 0C3.58 0 0 3.58",
        "M13.601 2.326",
        "M8 16s6-5.686",
    )
    if any(token not in social_svg for token in required_icons):
        fail("Social SVG does not contain all local interface icons")
    if any(token in social_svg for token in (">GH<", ">WA<", ">MX<")):
        fail("Social SVG still contains the old text monograms")


def validate_automation() -> None:
    workflow = ROOT / ".github" / "workflows" / "update-profile.yml"
    if not workflow.exists():
        fail("Missing automatic profile update workflow")
    source = workflow.read_text(encoding="utf-8")
    required = (
        'cron: "17 */6 * * *"',
        "workflow_dispatch:",
        "contents: write",
        "generate_profile_assets.py --strict-refresh",
        "data/profile-snapshot.json",
    )
    if any(token not in source for token in required):
        fail("Automatic profile workflow is incomplete")


def main() -> int:
    config = json.loads((ROOT / "data" / "profile.json").read_text(encoding="utf-8"))
    snapshot = json.loads(
        (ROOT / "data" / "profile-snapshot.json").read_text(encoding="utf-8")
    )
    total_size, gif_report = validate_gifs()
    validate_svgs()
    validate_chess(config)
    validate_snapshot(config, snapshot)
    validate_official_icons(config)
    validate_interface_icons()
    validate_automation()
    validate_readme()
    if not (ASSETS / "preview.png").exists():
        fail("Missing preview.png")
    print("Profile asset validation passed.")
    for item in gif_report:
        print(f"  {item}")
    print(f"  Total GIF size: {total_size / 1024 / 1024:.2f} MiB")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as error:
        print(f"Validation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
