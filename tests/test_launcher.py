"""Tests for SilentInstaller and install flag system (tasks 5.6, 5.9).

Property-based tests cover Property 5 from the design doc.
Unit tests cover the managed install directory and flag mechanism.
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from hypothesis import given, settings
from hypothesis import strategies as st

from src.launcher import (
    FLAG_FILE,
    InstallResult,
    SilentInstaller,
    installed_dir,
    is_installed,
)


# ---------------------------------------------------------------------------
# Task 5.6 — Property 5: SilentInstaller passes correct args by extension
# **Validates: Requirements 5.2, 5.5**
# ---------------------------------------------------------------------------

@given(
    stem=st.text(
        min_size=1,
        max_size=20,
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
    ),
    ext=st.sampled_from([".exe", ".msi"]),
    exit_code=st.integers(min_value=-1, max_value=5),
)
@settings(max_examples=100)
def test_silent_installer_correct_args(stem, ext, exit_code):
    """Property 5: SilentInstaller first attempt must pass correct silent params with target dir."""
    import tempfile, pathlib
    # Only test the success path (exit_code=0) to avoid fallback logic
    mock_success = InstallResult(success=True, exit_code=0)

    with tempfile.TemporaryDirectory() as tmp:
        setup_file = str(pathlib.Path(tmp) / f"{stem}_setup{ext}")
        pathlib.Path(setup_file).touch()
        target_dir = str(pathlib.Path(tmp) / "target")

        with patch.object(SilentInstaller, "_run_elevated", return_value=mock_success) as mock_run:
            with patch.object(SilentInstaller, "_detect_installer_type", return_value="nsis"):
                installer = SilentInstaller()
                result = installer.install(setup_file, target_dir)

        assert mock_run.called
        # Check the FIRST call (primary attempt with target dir)
        first_call_exe, first_call_params = mock_run.call_args_list[0][0]

        if ext == ".exe":
            assert first_call_exe == setup_file
            assert "/S" in first_call_params
            assert os.path.abspath(target_dir) in first_call_params
        else:
            assert "msiexec" in first_call_exe
            assert "/quiet" in first_call_params
            assert "/norestart" in first_call_params
            assert os.path.abspath(target_dir) in first_call_params

        assert result.success
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Task 5.9 — Unit tests for managed install directory and flag system
# ---------------------------------------------------------------------------

def test_installed_dir_path(tmp_path):
    """installed_dir() returns <exe_dir>/installed/<app>/<version>."""
    with patch("src.launcher._exe_dir", return_value=str(tmp_path)):
        result = installed_dir("MyApp", "v1.0")
    assert result == str(tmp_path / "installed" / "MyApp" / "v1.0")


def test_is_installed_returns_none_when_no_flag(tmp_path):
    """is_installed() returns None when flag file does not exist."""
    with patch("src.launcher._exe_dir", return_value=str(tmp_path)):
        assert is_installed("MyApp", "v1.0") is None


def test_is_installed_returns_exe_from_flag(tmp_path):
    """is_installed() returns the exe path stored in the flag file."""
    idir = tmp_path / "installed" / "MyApp" / "v1.0"
    idir.mkdir(parents=True)
    fake_exe = idir / "MyApp.exe"
    fake_exe.touch()
    flag = idir / FLAG_FILE
    flag.write_text(str(fake_exe), encoding="utf-8")

    with patch("src.launcher._exe_dir", return_value=str(tmp_path)):
        result = is_installed("MyApp", "v1.0")

    assert result == str(fake_exe)


def test_is_installed_scans_dir_when_flag_path_stale(tmp_path):
    """is_installed() falls back to scanning the dir when flag path no longer exists."""
    idir = tmp_path / "installed" / "MyApp" / "v1.0"
    idir.mkdir(parents=True)
    real_exe = idir / "MyApp.exe"
    real_exe.touch()
    # Flag points to a non-existent path
    flag = idir / FLAG_FILE
    flag.write_text("C:\\nonexistent\\old.exe", encoding="utf-8")

    with patch("src.launcher._exe_dir", return_value=str(tmp_path)):
        result = is_installed("MyApp", "v1.0")

    assert result == str(real_exe)


def test_is_installed_returns_none_when_flag_stale_and_no_exe(tmp_path):
    """is_installed() returns None when flag is stale and no exe in dir."""
    idir = tmp_path / "installed" / "MyApp" / "v1.0"
    idir.mkdir(parents=True)
    flag = idir / FLAG_FILE
    flag.write_text("C:\\nonexistent\\old.exe", encoding="utf-8")

    with patch("src.launcher._exe_dir", return_value=str(tmp_path)):
        result = is_installed("MyApp", "v1.0")

    assert result is None
