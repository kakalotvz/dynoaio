"""Tests for AppScanner and AppTypeDetector (tasks 5.1 – 5.5).

Unit tests cover specific examples and edge cases.
Property-based tests cover Properties 1–4 from the design doc.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from src.core import AppScanner, AppType, AppTypeDetector


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _touch(path: str) -> None:
    """Create an empty file (and any missing parent dirs)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").close()


# Windows reserved device names that cannot be used as directory names on Windows
_WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


# ---------------------------------------------------------------------------
# Task 5.1 — Unit tests for AppScanner
# ---------------------------------------------------------------------------

def test_scan_nonexistent_dir_returns_empty(tmp_path):
    scanner = AppScanner()
    result = scanner.scan(str(tmp_path / "does_not_exist"))
    assert result == []


def test_scan_empty_dir_returns_empty(tmp_path):
    apps_dir = tmp_path / "Apps"
    apps_dir.mkdir()
    scanner = AppScanner()
    result = scanner.scan(str(apps_dir))
    assert result == []


def test_scan_returns_one_app_per_subdir(tmp_path):
    apps_dir = tmp_path / "Apps"
    for name in ("Alpha", "Beta", "Gamma"):
        (apps_dir / name).mkdir(parents=True)
    scanner = AppScanner()
    result = scanner.scan(str(apps_dir))
    assert len(result) == 3


def test_scan_app_name_matches_dirname(tmp_path):
    apps_dir = tmp_path / "Apps"
    (apps_dir / "MyApp").mkdir(parents=True)
    scanner = AppScanner()
    result = scanner.scan(str(apps_dir))
    assert result[0].name == "MyApp"


def test_scan_flat_layout_creates_single_version(tmp_path):
    """App dir contains only files (no sub-dirs) → treated as one version."""
    apps_dir = tmp_path / "Apps"
    app_dir = apps_dir / "FlatApp"
    app_dir.mkdir(parents=True)
    _touch(str(app_dir / "FlatApp.exe"))
    scanner = AppScanner()
    result = scanner.scan(str(apps_dir))
    assert len(result) == 1
    assert len(result[0].versions) == 1
    assert result[0].versions[0].name == "FlatApp"


def test_scan_multi_version_layout(tmp_path):
    """App dir contains version sub-dirs with exe files → each sub-dir is a version."""
    apps_dir = tmp_path / "Apps"
    app_dir = apps_dir / "MultiApp"
    for ver in ("v1.0", "v2.0", "v3.0"):
        ver_dir = app_dir / ver
        ver_dir.mkdir(parents=True)
        (ver_dir / "app.exe").touch()  # need at least one exe for dir to be recognized
    scanner = AppScanner()
    result = scanner.scan(str(apps_dir))
    assert len(result) == 1
    assert len(result[0].versions) == 3
    version_names = {v.name for v in result[0].versions}
    assert version_names == {"v1.0", "v2.0", "v3.0"}


# ---------------------------------------------------------------------------
# Task 5.2 — Property 1: App scan reflects directory structure correctly
# **Validates: Requirements 1.1, 1.2**
# ---------------------------------------------------------------------------

_app_name_strategy = st.text(
    min_size=1,
    max_size=30,
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"),
        whitelist_characters="_- ",
    ),
).filter(lambda x: x.strip().upper() not in _WINDOWS_RESERVED and bool(x.strip()))


@given(
    app_names=st.lists(
        _app_name_strategy,
        min_size=0,
        max_size=10,
        unique=True,
    )
)
@settings(max_examples=100)
def test_scan_returns_correct_count(app_names):
    """Property 1: scan() count and names must match the created directories."""
    with tempfile.TemporaryDirectory() as tmp:
        apps_dir = Path(tmp) / "Apps"
        apps_dir.mkdir()
        # Strip whitespace and deduplicate by lower-case (Windows is case-insensitive)
        seen: set[str] = set()
        unique_names: list[str] = []
        for name in app_names:
            stripped = name.strip()
            if stripped and stripped.lower() not in seen:
                seen.add(stripped.lower())
                unique_names.append(stripped)
        for name in unique_names:
            (apps_dir / name).mkdir(exist_ok=True)

        scanner = AppScanner()
        result = scanner.scan(str(apps_dir))

        assert len(result) == len(unique_names)
        result_names = {app.name for app in result}
        assert result_names == set(unique_names)


# ---------------------------------------------------------------------------
# Task 5.3 — Property 2: Version scan reflects version directory structure
# **Validates: Requirements 2.1, 2.2**
# ---------------------------------------------------------------------------

_version_name_strategy = st.text(
    min_size=1,
    max_size=30,
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"),
        whitelist_characters="_- .",
    ),
).filter(
    lambda x: (
        x.strip().upper() not in _WINDOWS_RESERVED
        and bool(x.strip())
        # Reject names that are purely dots (e.g. ".", "..") — invalid as dir names
        and not all(c == "." for c in x.strip())
        # Windows silently strips trailing dots/spaces from directory names
        and not x.strip().endswith(".")
        and not x.strip().endswith(" ")
    )
)


@given(
    version_names=st.lists(
        _version_name_strategy,
        min_size=1,
        max_size=10,
        unique=True,
    )
)
@settings(max_examples=100, deadline=None)
def test_version_scan_count_and_names_match(version_names):
    """Property 2: version count and names must match the created version sub-dirs."""
    with tempfile.TemporaryDirectory() as tmp:
        apps_dir = Path(tmp) / "Apps"
        app_dir = apps_dir / "TestApp"
        # Deduplicate by lower-case (Windows is case-insensitive)
        seen: set[str] = set()
        unique_versions: list[str] = []
        for ver in version_names:
            stripped = ver.strip()
            if stripped and stripped.lower() not in seen:
                seen.add(stripped.lower())
                unique_versions.append(stripped)
        if not unique_versions:
            return
        for ver in unique_versions:
            ver_dir = app_dir / ver
            ver_dir.mkdir(parents=True, exist_ok=True)
            (ver_dir / "app.exe").touch()  # need exe so dir is recognized as version

        scanner = AppScanner()
        result = scanner.scan(str(apps_dir))

        assert len(result) == 1
        versions = result[0].versions
        assert len(versions) == len(unique_versions)
        result_ver_names = {v.name for v in versions}
        assert result_ver_names == set(unique_versions)


# ---------------------------------------------------------------------------
# Task 5.4 — Property 3: Classify as INSTALLABLE when setup file present
# **Validates: Requirements 3.1, 3.2**
# ---------------------------------------------------------------------------

@given(
    prefix=st.text(
        min_size=1,
        max_size=20,
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
    ),
    ext=st.sampled_from([".exe", ".msi"]),
)
@settings(max_examples=100, deadline=None)
def test_detect_installable_with_setup_file(prefix, ext):
    """Property 3: detect() must return INSTALLABLE when a *_setup.exe/.msi is present."""
    with tempfile.TemporaryDirectory() as tmp:
        setup_file = Path(tmp) / f"{prefix}_setup{ext}"
        setup_file.touch()

        detector = AppTypeDetector()
        result = detector.detect(tmp)

        assert result == AppType.INSTALLABLE


# ---------------------------------------------------------------------------
# Task 5.5 — Property 4: Classify as PORTABLE when no setup file
# **Validates: Requirements 3.1, 3.3**
# ---------------------------------------------------------------------------

@given(
    filenames=st.lists(
        st.text(
            min_size=1,
            max_size=20,
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
        ).filter(lambda x: "setup" not in x.lower()),
        min_size=0,
        max_size=10,
    )
)
@settings(max_examples=100, deadline=None)
def test_detect_portable_no_setup_files(filenames):
    """Property 4: detect() must return PORTABLE when non-setup .exe files exist,
    or EMPTY when no .exe files exist at all."""
    with tempfile.TemporaryDirectory() as tmp:
        for name in filenames:
            (Path(tmp) / f"{name}.txt").touch()  # .txt files — no exe

        detector = AppTypeDetector()
        result = detector.detect(tmp)

        # No .exe files at all → EMPTY (not PORTABLE)
        assert result == AppType.EMPTY


@given(
    filenames=st.lists(
        st.text(
            min_size=1,
            max_size=20,
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
        ).filter(lambda x: "setup" not in x.lower() and x),
        min_size=1,
        max_size=5,
    )
)
@settings(max_examples=100, deadline=None)
def test_detect_portable_with_exe_no_setup(filenames):
    """Property 4b: detect() must return PORTABLE when .exe files exist but none are setup."""
    with tempfile.TemporaryDirectory() as tmp:
        for name in filenames:
            (Path(tmp) / f"{name}.exe").touch()

        detector = AppTypeDetector()
        result = detector.detect(tmp)

        assert result == AppType.PORTABLE
