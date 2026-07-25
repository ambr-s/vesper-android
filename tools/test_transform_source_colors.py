# Copyright 2026 Vesper contributors
# SPDX-License-Identifier: AGPL-3.0-only

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import transform


def _make_source(
    tmp_path: Path,
    name: str,
    body: str,
    source_set: str = "main",
) -> Path:
    path = tmp_path / "app" / "src" / source_set / "java" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_rewrites_contextcompat_to_material_theme_attribute(tmp_path):
    source = _make_source(
        tmp_path,
        "Sample.kt",
        "package example\n\n"
        "import androidx.core.content.ContextCompat\n\n"
        "import org.thoughtcrime.securesms.R\n\n"
        "val c = ContextCompat.getColor("
        "context, CoreUiR.color.signal_colorOnSurface)\n",
    )

    changed = transform.transform_source_theme_colors(tmp_path)

    result = source.read_text(encoding="utf-8")
    assert changed == 1
    assert "import org.signal.core.ui.util.ThemeUtil" in result
    assert result.index("import org.signal.core.ui.util.ThemeUtil") < result.index(
        "import org.thoughtcrime.securesms.R"
    )
    assert "import androidx.core.content.ContextCompat" not in result
    assert (
        "ThemeUtil.getThemedColor("
        "context, com.google.android.material.R.attr.colorOnSurface)"
    ) in result
    assert "ContextCompat.getColor" not in result


def test_rewrites_contextcompat_to_core_ui_attribute(tmp_path):
    source = _make_source(
        tmp_path,
        "Surface.kt",
        "package example\n\n"
        "val c = ContextCompat.getColor("
        "requireContext(), CoreUiR.color.signal_colorSurface2)\n",
    )

    transform.transform_source_theme_colors(tmp_path)

    assert (
        "ThemeUtil.getThemedColor("
        "requireContext(), org.signal.core.ui.R.attr.vesper_colorSurface2)"
    ) in source.read_text(encoding="utf-8")


def test_rewrites_contextcompat_to_app_attribute(tmp_path):
    source = _make_source(
        tmp_path,
        "Legacy.java",
        "package example;\n\n"
        "import android.content.Context;\n\n"
        "class Legacy {\n"
        "  int c = ContextCompat.getColor("
        "context, R.color.conversation_item_recv_bubble_color_normal);\n"
        "}\n",
    )

    transform.transform_source_theme_colors(tmp_path)

    result = source.read_text(encoding="utf-8")
    assert "import org.signal.core.ui.util.ThemeUtil;" in result
    assert result.startswith(
        "package example;\n\n"
        "import org.signal.core.ui.util.ThemeUtil;\n\n"
        "import android.content.Context;\n"
    )
    assert (
        "ThemeUtil.getThemedColor("
        "context, R.attr.conversation_item_recv_bubble_color_normal)"
    ) in result


def test_rewrites_receiver_resources_get_color(tmp_path):
    source = _make_source(
        tmp_path,
        "Resources.java",
        "package example;\n\n"
        "class Resources {\n"
        "  int c = getContext().getResources().getColor("
        "org.signal.core.ui.R.color.signal_colorOnSurface);\n"
        "}\n",
    )

    transform.transform_source_theme_colors(tmp_path)

    assert (
        "ThemeUtil.getThemedColor("
        "getContext(), com.google.android.material.R.attr.colorOnSurface)"
    ) in source.read_text(encoding="utf-8")


def test_rewrites_compose_color_resource(tmp_path):
    source = _make_source(
        tmp_path,
        "Compose.kt",
        "package example\n\n"
        "import androidx.compose.ui.res.colorResource\n\n"
        "@Composable\n"
        "fun Content() {\n"
        "  val c = colorResource(R.color.signal_text_primary)\n"
        "}\n",
    )

    transform.transform_source_theme_colors(tmp_path)

    result = source.read_text(encoding="utf-8")
    assert "import org.signal.core.ui.compose.theme.colorAttribute" in result
    assert "colorAttribute(R.attr.signal_text_primary)" in result
    assert "colorResource(R.color.signal_text_primary)" not in result


def test_leaves_unmapped_colors_and_contextless_resource_calls_alone(tmp_path):
    source = _make_source(
        tmp_path,
        "Other.kt",
        "package example\n\n"
        "val a = ContextCompat.getColor(context, R.color.some_unmapped_color)\n"
        "val b = getResources().getColor(R.color.signal_text_primary)\n",
    )

    changed = transform.transform_source_theme_colors(tmp_path)

    result = source.read_text(encoding="utf-8")
    assert changed == 0
    assert "ContextCompat.getColor" in result
    assert "getResources().getColor" in result


def test_ignores_non_main_source_sets(tmp_path):
    source = _make_source(
        tmp_path,
        "Sample.kt",
        "val c = ContextCompat.getColor("
        "context, CoreUiR.color.signal_colorOnSurface)\n",
        source_set="test",
    )

    changed = transform.transform_source_theme_colors(tmp_path)

    assert changed == 0
    assert "ContextCompat.getColor" in source.read_text(encoding="utf-8")
