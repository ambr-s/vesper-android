#!/usr/bin/env python3
# Copyright 2026 Vesper contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Apply Vesper's pattern-based transforms to a Signal checkout."""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "branding" / "vesper.env"
STRING_MANIFEST_PATH = ROOT / "branding" / "strings-manifest.txt"
COLORS_PATH = (
    ROOT
    / "overlay"
    / "core"
    / "ui"
    / "src"
    / "main"
    / "res"
    / "values"
    / "vesper_colors.xml"
)

THEME_COLOR_REFERENCES = {
    "signal_colorPrimary": "colorPrimary",
    "signal_colorPrimaryContainer": "colorPrimaryContainer",
    "signal_colorSecondary": "colorSecondary",
    "signal_colorSecondaryContainer": "colorSecondaryContainer",
    "signal_colorSurface": "colorSurface",
    "signal_colorSurfaceVariant": "colorSurfaceVariant",
    "signal_colorSurface1": "vesper_colorSurface1",
    "signal_colorSurface2": "vesper_colorSurface2",
    "signal_colorSurface3": "vesper_colorSurface3",
    "signal_colorSurface4": "vesper_colorSurface4",
    "signal_colorSurface5": "vesper_colorSurface5",
    "signal_colorBackground": "colorSurface",
    "signal_colorError": "colorError",
    "signal_colorErrorContainer": "colorErrorContainer",
    "signal_colorOnPrimary": "colorOnPrimary",
    "signal_colorOnPrimaryContainer": "colorOnPrimaryContainer",
    "signal_colorOnSecondary": "colorOnSecondary",
    "signal_colorOnSecondaryContainer": "colorOnSecondaryContainer",
    "signal_colorOnSurface": "colorOnSurface",
    "signal_colorOnSurfaceVariant": "colorOnSurfaceVariant",
    "signal_colorOnBackground": "colorOnBackground",
    "signal_colorOutline": "colorOutline",
    "signal_colorOnSurfaceInverse": "colorOnSurfaceInverse",
    # Signal's legacy semantic colours are static resources upstream. Molly
    # promotes them to theme attributes so legacy views participate in
    # Material You just like Material and Compose surfaces do.
    "conversation_toolbar_color": "conversation_toolbar_color",
    "signal_accent_primary": "signal_accent_primary",
    "signal_background_primary": "signal_background_primary",
    "signal_background_secondary": "signal_background_secondary",
    "signal_background_dialog": "signal_background_dialog",
    "signal_background_dialog_secondary": "signal_background_dialog_secondary",
    "signal_text_primary": "signal_text_primary",
    "signal_text_secondary": "signal_text_secondary",
    "signal_text_toolbar_title": "signal_text_toolbar_title",
    "signal_icon_tint_primary": "signal_icon_tint_primary",
    "signal_icon_tint_secondary": "signal_icon_tint_secondary",
    "signal_icon_tint_action": "signal_icon_tint_action",
    "signal_icon_tint_tab_selected": "signal_icon_tint_tab_selected",
    "signal_icon_tint_tab_unselected": "signal_icon_tint_tab_unselected",
    "signal_button_primary": "signal_button_primary",
    "signal_button_primary_ripple": "signal_button_primary_ripple",
    "signal_button_primary_text": "signal_button_primary_text",
    "signal_button_primary_text_disabled": "signal_button_primary_text_disabled",
    "signal_button_secondary": "signal_button_secondary",
    "signal_button_secondary_ripple": "signal_button_secondary_ripple",
    "signal_button_secondary_text": "signal_button_secondary_text",
    "signal_button_secondary_text_disabled": "signal_button_secondary_text_disabled",
    "signal_button_secondary_stroke": "signal_button_secondary_stroke",
    "conversation_compose_background": "conversation_compose_background",
    "contact_filter_edit_background": "contact_filter_edit_background",
    "reactions_pill_selected_color": "reactions_pill_selected_color",
    "qr_card_color": "qr_card_color",
    "qr_card_text_color": "qr_card_text_color",
    "conversation_item_update_text_color": "conversation_item_update_text_color",
    "conversation_item_quote_text_color": "conversation_item_quote_text_color",
    "conversation_item_quote_text_color_sent": "conversation_item_quote_text_color_sent",
    "conversation_item_recv_bubble_color_normal": "conversation_item_recv_bubble_color_normal",
    "conversation_item_incoming_audio_foreground_tint_normal": "conversation_item_incoming_audio_foreground_tint_normal",
    "conversation_typing_indicator_foreground_tint_normal": "conversation_typing_indicator_foreground_tint_normal",
    "conversation_scroll_to_bottom_foreground_color": "conversation_scroll_to_bottom_foreground_color",
    "conversation_list_selected_color": "conversation_list_selected_color",
    "reactions_pill_text_color": "reactions_pill_text_color",
    "reactions_overlay_any_emoji_background": "reactions_overlay_any_emoji_background",
    "reactions_overlay_any_emoji_foreground": "reactions_overlay_any_emoji_foreground",
    "megaphone_body_text_color": "megaphone_body_text_color",
    "tooltip_default_color": "tooltip_default_color",
    "quote_view_background_incoming_wallpaper": "quote_view_background_incoming_wallpaper",
    "quote_view_bar_incoming_wallpaper": "quote_view_bar_incoming_wallpaper",
    "quote_view_foreground_incoming_wallpaper": "quote_view_foreground_incoming_wallpaper",
    "quote_view_background_outgoing_wallpaper": "quote_view_background_outgoing_wallpaper",
    "quote_view_bar_outgoing_wallpaper": "quote_view_bar_outgoing_wallpaper",
    "quote_view_foreground_outgoing_wallpaper": "quote_view_foreground_outgoing_wallpaper",
    "quote_view_background_incoming_normal": "quote_view_background_incoming_normal",
    "quote_view_bar_incoming_normal": "quote_view_bar_incoming_normal",
    "quote_view_foreground_incoming_normal": "quote_view_foreground_incoming_normal",
    "quote_view_background_outgoing_normal": "quote_view_background_outgoing_normal",
    "quote_view_bar_outgoing_normal": "quote_view_bar_outgoing_normal",
    "quote_view_foreground_outgoing_normal": "quote_view_foreground_outgoing_normal",
    "quote_view_label_background_incoming_normal": "quote_view_label_background_incoming_normal",
    "quote_view_label_background_incoming_wallpaper": "quote_view_label_background_incoming_wallpaper",
    "quote_view_label_background_outgoing_normal": "quote_view_label_background_outgoing_normal",
    "quote_view_label_background_outgoing_wallpaper": "quote_view_label_background_outgoing_wallpaper",
    "react_with_any_background": "react_with_any_background",
    "react_with_any_search_background": "react_with_any_search_background",
    "react_with_any_search_hint": "react_with_any_search_hint",
    "react_with_any_customize_background": "react_with_any_customize_background",
    "voice_note_player_view_background": "voice_note_player_view_background",
    "message_request_bar_container_background_normal": "message_request_bar_container_background_normal",
    "message_request_bar_background_normal": "message_request_bar_background_normal",
    "message_request_bar_denyForeground_normal": "message_request_bar_denyForeground_normal",
    "message_request_bar_acceptForeground_normal": "message_request_bar_acceptForeground_normal",
    "message_request_bar_container_background_wallpaper": "message_request_bar_container_background_wallpaper",
    "message_request_bar_background_wallpaper": "message_request_bar_background_wallpaper",
    "message_request_bar_denyForeground_wallpaper": "message_request_bar_denyForeground_wallpaper",
    "message_request_bar_acceptForeground_wallpaper": "message_request_bar_acceptForeground_wallpaper",
    "safety_tip_background": "safety_tip_background",
    "safety_tip_image_background": "safety_tip_image_background",
}

MATERIAL_ATTRIBUTE_PREFIX = "com.google.android.material.R.attr"
CORE_UI_ATTRIBUTE_PREFIX = "org.signal.core.ui.R.attr"
APP_ATTRIBUTE_PREFIX = "R.attr"


def qualified_attribute(attribute: str) -> str:
    if attribute.startswith("vesper_"):
        return f"{CORE_UI_ATTRIBUTE_PREFIX}.{attribute}"
    if attribute.startswith("color"):
        return f"{MATERIAL_ATTRIBUTE_PREFIX}.{attribute}"
    return f"{APP_ATTRIBUTE_PREFIX}.{attribute}"


def load_config(path: Path) -> dict[str, str]:
    config: dict[str, str] = {}
    for number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"{path}:{number}: expected KEY=VALUE")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            raise ValueError(f"{path}:{number}: invalid key {key!r}")
        if not value:
            raise ValueError(f"{path}:{number}: empty value for {key}")
        config[key] = value

    required = {"APP_TITLE", "APP_FILE_NAME", "PACKAGE_ID", "UPDATE_MANIFEST_URL"}
    missing = sorted(required - config.keys())
    if missing:
        raise ValueError(f"{path}: missing keys: {', '.join(missing)}")
    return config


def replace_exactly_once(text: str, old: str, new: str, description: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"{description}: expected exactly one upstream match, found {count}"
        )
    return text.replace(old, new, 1)


def transform_gradle(checkout: Path, config: dict[str, str]) -> None:
    app_gradle = checkout / "app" / "build.gradle.kts"
    text = app_gradle.read_text(encoding="utf-8")

    application_id = f'    applicationId = "{config["PACKAGE_ID"]}"\n'
    if application_id not in text:
        text = replace_exactly_once(
            text,
            "  defaultConfig {\n",
            "  defaultConfig {\n" + application_id,
            "application id transform",
        )

    archive_old = '    project.ext.set("archivesBaseName", "Signal")'
    archive_new = (
        f'    project.ext.set("archivesBaseName", "{config["APP_FILE_NAME"]}")'
    )
    if archive_new not in text:
        text = replace_exactly_once(
            text, archive_old, archive_new, "APK filename transform"
        )

    updater_old = (
        '      buildConfigField("String", "APK_UPDATE_MANIFEST_URL", '
        '"\\"https://updates.signal.org/android/latest.json\\"")'
    )
    updater_new = (
        '      buildConfigField("String", "APK_UPDATE_MANIFEST_URL", '
        f'"\\"{config["UPDATE_MANIFEST_URL"]}\\"")'
    )
    if updater_new not in text:
        text = replace_exactly_once(
            text, updater_old, updater_new, "website updater URL transform"
        )

    app_gradle.write_text(text, encoding="utf-8")

    root_gradle = checkout / "build.gradle.kts"
    text = root_gradle.read_text(encoding="utf-8")
    plugin_line = '  id("vesperify")\n'
    if plugin_line not in text:
        text = replace_exactly_once(
            text,
            '  id("dependency-verification")\n',
            '  id("dependency-verification")\n' + plugin_line,
            "Vesper Gradle plugin transform",
        )
    root_gradle.write_text(text, encoding="utf-8")

    vesper_dir = checkout / ".vesper"
    vesper_dir.mkdir(exist_ok=True)
    (vesper_dir / "strings-manifest.txt").write_text(
        STRING_MANIFEST_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )


RESOURCE_PATTERN = re.compile(
    r"<(?P<tag>string|plurals)\b"
    r"(?P<attrs>[^>]*?\bname\s*=\s*[\"'](?P<name>[^\"']+)[\"'][^>]*)>"
    r"(?P<body>.*?)"
    r"</(?P=tag)>",
    re.DOTALL,
)


def is_main_strings_file(path: Path) -> bool:
    parts = path.parts
    try:
        src_index = parts.index("src")
    except ValueError:
        return False
    return (
        len(parts) > src_index + 4
        and parts[src_index + 1] == "main"
        and parts[src_index + 2] == "res"
        and parts[src_index + 3].startswith("values")
        and path.name == "strings.xml"
    )


def load_string_manifest(path: Path) -> set[str]:
    names = {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    if not names:
        raise RuntimeError(f"{path}: string manifest is empty")
    return names


def transform_strings(
    checkout: Path, config: dict[str, str], manifest: set[str]
) -> tuple[int, set[str]]:
    changed_files = 0
    seen: set[str] = set()

    def replace_resource(match: re.Match[str]) -> str:
        name = match.group("name")
        body = match.group("body")
        if name in manifest:
            seen.add(name)
            body = body.replace("Signal", config["APP_TITLE"])
        if name == "app_name":
            body = body.replace("Signal", config["APP_TITLE"])
        return (
            f'<{match.group("tag")}{match.group("attrs")}>'
            f"{body}</{match.group('tag')}>"
        )

    for strings_file in sorted(checkout.rglob("strings.xml")):
        if not is_main_strings_file(strings_file):
            continue
        original = strings_file.read_text(encoding="utf-8")
        updated = RESOURCE_PATTERN.sub(replace_resource, original)
        if updated != original:
            strings_file.write_text(updated, encoding="utf-8")
            changed_files += 1

    return changed_files, manifest - seen


def load_color_mappings(path: Path) -> list[tuple[str, str]]:
    colors: dict[str, str] = {}
    for element in ET.parse(path).getroot().findall("color"):
        name = element.attrib.get("name")
        value = (element.text or "").strip().removeprefix("#").upper()
        if name and re.fullmatch(r"[0-9A-F]{6}", value):
            colors[name] = value

    mappings: set[tuple[str, str]] = set()
    missing: list[str] = []
    for stock_name, stock_value in colors.items():
        if not stock_name.startswith("stock_"):
            continue
        vesper_name = stock_name.replace("stock_", "vesper_", 1)
        vesper_value = colors.get(vesper_name)
        if vesper_value is None:
            missing.append(vesper_name)
        else:
            mappings.add((stock_value, vesper_value))

    if missing:
        raise RuntimeError(
            f"{path}: missing Vesper colours for: {', '.join(sorted(missing))}"
        )

    stock_targets: defaultdict[str, set[str]] = defaultdict(set)
    vesper_sources: defaultdict[str, set[str]] = defaultdict(set)
    for stock, vesper in mappings:
        stock_targets[stock].add(vesper)
        vesper_sources[vesper].add(stock)

    conflicts = {
        stock: targets for stock, targets in stock_targets.items() if len(targets) > 1
    }
    reverse_conflicts = {
        vesper: sources
        for vesper, sources in vesper_sources.items()
        if len(sources) > 1
    }
    cycle_values = (stock_targets.keys() & vesper_sources.keys()) - {
        value
        for value in stock_targets.keys() & vesper_sources.keys()
        if stock_targets[value] == {value} and vesper_sources[value] == {value}
    }
    if conflicts or reverse_conflicts or cycle_values:
        raise RuntimeError(
            f"{path}: ambiguous or circular colour mappings; "
            f"forward={dict(conflicts)}, reverse={dict(reverse_conflicts)}, "
            f"cycles={sorted(cycle_values)}"
        )

    return sorted(mappings)


def is_brandable_source(path: Path, palette_target: Path) -> bool:
    if path == palette_target:
        return False
    if path.suffix not in {".xml", ".kt", ".java"}:
        return False
    if path.name.startswith("strings") and path.suffix == ".xml":
        return False
    parts = path.parts
    try:
        src_index = parts.index("src")
    except ValueError:
        return False
    return len(parts) > src_index + 1 and parts[src_index + 1] == "main"


def transform_colors(checkout: Path, mappings: list[tuple[str, str]]) -> int:
    palette_target = (
        checkout
        / "core"
        / "ui"
        / "src"
        / "main"
        / "res"
        / "values"
        / "vesper_colors.xml"
    )
    replacements = [
        (
            re.compile(
                rf"(?i)(?P<prefix>0x|#)(?P<alpha>[0-9a-f]{{2}})?"
                rf"(?P<hex>{re.escape(stock)})\b"
            ),
            vesper,
        )
        for stock, vesper in mappings
        if stock != vesper
    ]

    changed_files = 0
    for path in sorted(checkout.rglob("*")):
        if not path.is_file() or not is_brandable_source(path, palette_target):
            continue
        try:
            original = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        updated = original
        for pattern, vesper in replacements:
            updated = pattern.sub(
                lambda match: (
                    f"{match.group('prefix')}{match.group('alpha') or ''}{vesper}"
                ),
                updated,
            )
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed_files += 1
    return changed_files


def is_themeable_resource_xml(path: Path) -> bool:
    if path.suffix != ".xml":
        return False
    parts = path.parts
    try:
        src_index = parts.index("src")
    except ValueError:
        return False
    if (
        len(parts) <= src_index + 4
        or parts[src_index + 1] != "main"
        or parts[src_index + 2] != "res"
    ):
        return False
    return not parts[src_index + 3].startswith("values")


def is_values_resource_xml(path: Path) -> bool:
    if path.suffix != ".xml":
        return False
    parts = path.parts
    try:
        src_index = parts.index("src")
    except ValueError:
        return False
    return (
        len(parts) > src_index + 4
        and parts[src_index + 1] == "main"
        and parts[src_index + 2] == "res"
        and parts[src_index + 3].startswith("values")
    )


STYLE_ITEM_PATTERN = re.compile(
    r"(?P<indent>^[ \t]*)"
    r"<item\b"
    r"(?P<attrs>(?=[^>]*\bname\s*=\s*[\"'])[^>]*)>"
    r"(?P<body>.*?)"
    r"</item>",
    re.DOTALL | re.MULTILINE,
)


def transform_theme_color_references(checkout: Path) -> int:
    replacements = sorted(
        (
            (
                re.compile(
                    rf"{re.escape(f'@color/{resource}')}(?![A-Za-z0-9_])"
                ),
                f"?attr/{attribute}",
            )
            for resource, attribute in THEME_COLOR_REFERENCES.items()
        ),
        key=lambda replacement: len(replacement[0].pattern),
        reverse=True,
    )

    changed_files = 0
    for path in sorted(checkout.rglob("*.xml")):
        if not path.is_file() or not (
            is_themeable_resource_xml(path) or is_values_resource_xml(path)
        ):
            continue
        original = path.read_text(encoding="utf-8")

        def replace_color_references(text: str) -> str:
            for resource, attribute in replacements:
                text = resource.sub(attribute, text)
            return text

        if is_values_resource_xml(path):
            def replace_style_item(match: re.Match[str]) -> str:
                attrs = match.group("attrs")
                if re.search(r"\btype\s*=\s*[\"']color[\"']", attrs):
                    return match.group(0)

                item_name_match = re.search(
                    r"\bname\s*=\s*[\"'](?P<name>[^\"']+)[\"']", attrs
                )
                color_reference_match = re.fullmatch(
                    r"\s*@color/(?P<resource>[A-Za-z0-9_]+)\s*",
                    match.group("body"),
                )
                if item_name_match and color_reference_match:
                    item_name = item_name_match.group("name").split(":")[-1]
                    mapped_attribute = THEME_COLOR_REFERENCES.get(
                        color_reference_match.group("resource")
                    )
                    # A theme overlay that assigns an attribute back to itself
                    # creates a resource cycle. Dropping the static override lets
                    # the dynamic value from the parent theme flow through.
                    if mapped_attribute == item_name:
                        return ""

                return (
                    f"{match.group('indent')}<item{attrs}>"
                    f"{replace_color_references(match.group('body'))}"
                    "</item>"
                )

            updated = STYLE_ITEM_PATTERN.sub(replace_style_item, original)
        else:
            updated = replace_color_references(original)

        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed_files += 1
    return changed_files


SOURCE_COLOR_REFERENCE = (
    r"(?:CoreUiR|org\.signal\.core\.ui\.R|R)"
    r"\.color\.(?P<resource>[A-Za-z0-9_]+)"
)
CONTEXT_COMPAT_COLOR_PATTERN = re.compile(
    r"ContextCompat\.getColor\(\s*"
    r"(?P<context>[^,\n]+?)\s*,\s*"
    + SOURCE_COLOR_REFERENCE
    + r"\s*\)"
)
RESOURCES_COLOR_PATTERN = re.compile(
    r"(?P<context>[A-Za-z_][A-Za-z0-9_.]*(?:\(\))?)"
    r"\.getResources\(\)\.getColor\(\s*"
    + SOURCE_COLOR_REFERENCE
    + r"\s*\)"
)
COMPOSE_COLOR_PATTERN = re.compile(
    r"colorResource\(\s*" + SOURCE_COLOR_REFERENCE + r"\s*\)"
)

THEME_UTIL_IMPORT_KT = "import org.signal.core.ui.util.ThemeUtil"
THEME_UTIL_IMPORT_JAVA = "import org.signal.core.ui.util.ThemeUtil;"
COLOR_ATTRIBUTE_IMPORT = "import org.signal.core.ui.compose.theme.colorAttribute"


def _add_source_import(text: str, statement: str) -> str:
    if statement in text:
        return text

    lines = text.split("\n")
    if statement.endswith(";"):
        packages = [
            index for index, line in enumerate(lines) if line.startswith("package ")
        ]
        insert_at = packages[-1] + 1 if packages else 0
        if insert_at < len(lines) and not lines[insert_at]:
            insert_at += 1
            lines[insert_at:insert_at] = [statement, ""]
        else:
            lines[insert_at:insert_at] = ["", statement, ""]
        return "\n".join(lines)

    imports = [index for index, line in enumerate(lines) if line.startswith("import ")]
    if imports:
        statement_key = (" as " in statement, statement)
        insert_at = imports[-1] + 1
        for index in imports:
            line = lines[index]
            if (" as " in line, line) > statement_key:
                insert_at = index
                break
    else:
        packages = [
            index for index, line in enumerate(lines) if line.startswith("package ")
        ]
        insert_at = packages[-1] + 1 if packages else 0
        if insert_at < len(lines) and lines[insert_at]:
            lines.insert(insert_at, "")
            insert_at += 1
    lines.insert(insert_at, statement)
    return "\n".join(lines)


def _remove_unused_kotlin_color_imports(text: str) -> str:
    imports = (
        (
            "ContextCompat.",
            "import androidx.core.content.ContextCompat\n",
        ),
        (
            "colorResource(",
            "import androidx.compose.ui.res.colorResource\n",
        ),
        (
            "CoreUiR.",
            "import org.signal.core.ui.R as CoreUiR\n",
        ),
    )
    for reference, statement in imports:
        if reference not in text.replace(statement, ""):
            text = text.replace(statement, "")
    return text


def transform_source_theme_colors(checkout: Path) -> int:
    palette_target = (
        checkout
        / "core"
        / "ui"
        / "src"
        / "main"
        / "res"
        / "values"
        / "vesper_colors.xml"
    )

    def replace_context_call(match: re.Match[str]) -> str:
        attribute = THEME_COLOR_REFERENCES.get(match.group("resource"))
        if attribute is None:
            return match.group(0)
        return (
            f"ThemeUtil.getThemedColor({match.group('context').strip()}, "
            f"{qualified_attribute(attribute)})"
        )

    def replace_compose_call(match: re.Match[str]) -> str:
        attribute = THEME_COLOR_REFERENCES.get(match.group("resource"))
        if attribute is None:
            return match.group(0)
        return f"colorAttribute({qualified_attribute(attribute)})"

    changed_files = 0
    for path in sorted(checkout.rglob("*")):
        if not path.is_file() or path.suffix not in {".kt", ".java"}:
            continue
        if not is_brandable_source(path, palette_target):
            continue
        try:
            original = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        updated = RESOURCES_COLOR_PATTERN.sub(replace_context_call, original)
        updated = CONTEXT_COMPAT_COLOR_PATTERN.sub(replace_context_call, updated)
        uses_theme_util = updated != original

        compose_updated = COMPOSE_COLOR_PATTERN.sub(replace_compose_call, updated)
        uses_color_attribute = compose_updated != updated
        updated = compose_updated

        if uses_theme_util:
            updated = _add_source_import(
                updated,
                THEME_UTIL_IMPORT_JAVA
                if path.suffix == ".java"
                else THEME_UTIL_IMPORT_KT,
            )
        if uses_color_attribute:
            updated = _add_source_import(updated, COLOR_ATTRIBUTE_IMPORT)
        if path.suffix == ".kt" and (uses_theme_util or uses_color_attribute):
            updated = _remove_unused_kotlin_color_imports(updated)

        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed_files += 1

    return changed_files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "checkout", type=Path, help="materialised Signal checkout to transform"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    checkout = args.checkout.resolve()
    if not (checkout / ".git").exists() or not (checkout / "app").is_dir():
        raise RuntimeError(f"{checkout}: not a Signal git checkout")

    config = load_config(CONFIG_PATH)
    manifest = load_string_manifest(STRING_MANIFEST_PATH)
    mappings = load_color_mappings(COLORS_PATH)

    transform_gradle(checkout, config)
    string_files, missing_strings = transform_strings(checkout, config, manifest)
    themed_resource_files = transform_theme_color_references(checkout)
    themed_source_files = transform_source_theme_colors(checkout)
    color_files = transform_colors(checkout, mappings)

    print(f"Vesper branding: updated {string_files} string resource files")
    print(
        "Vesper branding: updated "
        f"{themed_resource_files} theme-aware resource files"
    )
    print(f"Vesper branding: updated {themed_source_files} themed source files")
    print(f"Vesper branding: updated colours in {color_files} source files")
    if missing_strings:
        print(
            "warning: string manifest entries absent from this Signal release:\n  "
            + "\n  ".join(sorted(missing_strings)),
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
