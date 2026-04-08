from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field

from src.core import AppType, VersionInfo


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _exe_dir() -> str:
    """Directory of the running exe (or project root in dev mode)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(sys.argv[0]))


def installed_dir(app_name: str, version_name: str) -> str:
    """Return the managed install directory for a specific app version."""
    return os.path.join(_exe_dir(), "installed", app_name, version_name)


FLAG_FILE = "installed.flag"


def is_installed(app_name: str, version_name: str) -> str | None:
    """Return path to the main exe if this version is already installed, else None."""
    idir = installed_dir(app_name, version_name)
    flag = os.path.join(idir, FLAG_FILE)
    if not os.path.isfile(flag):
        return None
    # Read exe path stored in the flag file
    try:
        exe = open(flag, encoding="utf-8").read().strip()
        if exe and os.path.isfile(exe):
            return exe
    except OSError:
        pass
    # Flag exists but exe path is stale — xóa flag để tránh false positive
    try:
        os.remove(flag)
    except OSError:
        pass
    return None


def _find_exe_in_dir(directory: str) -> str | None:
    try:
        for entry in sorted(os.scandir(directory), key=lambda e: e.name):
            if entry.is_file() and entry.name.lower().endswith(".exe"):
                return entry.path
    except (FileNotFoundError, NotADirectoryError, PermissionError):
        pass
    return None


def _find_via_registry(app_name: str) -> str | None:
    """Look up InstallLocation or DisplayIcon in Uninstall registry keys."""
    try:
        import winreg  # type: ignore[import]
    except ImportError:
        return None
    hives = [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]
    sub_keys = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    ]
    # Require all words of app_name to appear in DisplayName
    name_words = [w.lower() for w in app_name.split() if w]
    for hive in hives:
        for sub_key in sub_keys:
            try:
                with winreg.OpenKey(hive, sub_key) as key:
                    i = 0
                    while True:
                        try:
                            sub_name = winreg.EnumKey(key, i); i += 1
                        except OSError:
                            break
                        try:
                            with winreg.OpenKey(key, sub_name) as sub:
                                def _val(name):
                                    try:
                                        v, _ = winreg.QueryValueEx(sub, name)
                                        return v if isinstance(v, str) else None
                                    except OSError:
                                        return None
                                display = (_val("DisplayName") or "").lower()
                                # All words of app_name must appear in DisplayName
                                if not all(w in display for w in name_words):
                                    continue
                                loc = _val("InstallLocation")
                                if loc:
                                    exe = _find_exe_in_dir(loc)
                                    if exe:
                                        return exe
                                icon = _val("DisplayIcon")
                                if icon:
                                    p = icon.split(",")[0].strip().strip('"')
                                    if p.lower().endswith(".exe") and os.path.isfile(p):
                                        return p
                        except OSError:
                            continue
            except OSError:
                continue
    return None


def _snapshot_program_files() -> dict[str, float]:
    """Snapshot all exe files in Program Files dirs with their mtime."""
    snapshot: dict[str, float] = {}
    roots = []
    for var in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
        p = os.environ.get(var)
        if p and os.path.isdir(p) and p not in roots:
            roots.append(p)
    for root in roots:
        try:
            for app_dir in os.scandir(root):
                if not app_dir.is_dir():
                    continue
                try:
                    for entry in os.scandir(app_dir.path):
                        if entry.is_file() and entry.name.lower().endswith(".exe"):
                            snapshot[entry.path] = entry.stat().st_mtime
                except (PermissionError, OSError):
                    continue
        except (PermissionError, OSError):
            continue
    return snapshot


def _find_new_exe_in_program_files(before: dict[str, float],
                                    app_name: str = "",
                                    version_name: str = "") -> str | None:
    """Find exe files that appeared in Program Files after install."""
    after = _snapshot_program_files()
    name_hints = [w.lower() for w in (app_name + " " + version_name).split()
                  if len(w) > 2]

    new_exes = [p for p in after if p not in before and os.path.isfile(p)]

    if not new_exes:
        return None

    # Score by name match
    if name_hints:
        scored = []
        for exe in new_exes:
            exe_lower = exe.lower()
            score = sum(1 for h in name_hints if h in exe_lower)
            scored.append((score, exe))
        scored.sort(reverse=True)
        if scored[0][0] > 0:
            return scored[0][1]
        # No name match but only one new exe — return it
        if len(new_exes) == 1:
            return new_exes[0]
        return None

    if len(new_exes) == 1:
        return new_exes[0]
    return None


def clear_install_flag(app_name: str, version_name: str) -> None:
    """Xóa flag file sau khi gỡ cài đặt."""
    flag = os.path.join(installed_dir(app_name, version_name), FLAG_FILE)
    try:
        os.remove(flag)
    except OSError:
        pass


def _launch_exe(exe_path: str) -> "LaunchResult":
    """Launch an exe. ShellExecuteW primary (handles UAC), subprocess fallback."""
    import ctypes
    exe_path = os.path.abspath(exe_path)
    work_dir = os.path.dirname(exe_path)
    try:
        # ShellExecuteW với "open" — Windows tự xử lý UAC manifest của app
        ret = ctypes.windll.shell32.ShellExecuteW(None, "open", exe_path, None, work_dir, 1)
        if ret > 32:
            return LaunchResult(success=True, message="")
        # Nếu cần elevation thì dùng runas
        ret2 = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe_path, None, work_dir, 1)
        if ret2 > 32:
            return LaunchResult(success=True, message="")
        return LaunchResult(success=False, message=f"Không thể mở ứng dụng (code {ret})")
    except Exception as exc:
        return LaunchResult(success=False, message=str(exc))


def _find_in_program_files(app_name: str) -> str | None:
    """Search Program Files directories for a matching app folder."""
    roots = []
    for var in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
        p = os.environ.get(var)
        if p and os.path.isdir(p) and p not in roots:
            roots.append(p)
    lower_name = app_name.lower()
    for root in roots:
        try:
            for entry in os.scandir(root):
                if entry.is_dir() and lower_name in entry.name.lower():
                    exe = _find_exe_in_dir(entry.path)
                    if exe:
                        return exe
        except PermissionError:
            continue
    return None


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class LaunchResult:
    success: bool
    message: str


@dataclass
class InstallResult:
    success: bool
    exit_code: int
    error: str = ""


# ---------------------------------------------------------------------------
# PortableRunner
# ---------------------------------------------------------------------------

class PortableRunner:
    """Find and launch the first .exe in a version directory that is not a setup file."""

    def run(self, version_path: str) -> LaunchResult:
        try:
            entries = os.listdir(version_path)
        except (FileNotFoundError, NotADirectoryError, PermissionError):
            return LaunchResult(success=False, message="Không tìm thấy file thực thi")

        for entry in sorted(entries):
            if entry.lower().endswith(".exe") and "setup" not in entry.lower():
                exe_path = os.path.join(version_path, entry)
                return _launch_exe(exe_path)

        return LaunchResult(success=False, message="Không tìm thấy file thực thi")


# ---------------------------------------------------------------------------
# SilentInstaller
# ---------------------------------------------------------------------------

class SilentInstaller:
    """Run a setup file silently, auto-detecting installer type."""

    _DIR_PARAM_REJECTED_CODES = {1155, 1203, 1638, 1, 2}

    def install(self, setup_file: str, target_dir: str) -> InstallResult:
        setup_file = os.path.abspath(setup_file)
        target_dir = os.path.abspath(target_dir)

        if not os.path.isfile(setup_file):
            return InstallResult(success=False, exit_code=-1,
                                 error="Không tìm thấy tệp cài đặt của phần mềm.")
        try:
            os.makedirs(target_dir, exist_ok=True)
            lower = setup_file.lower()

            if lower.endswith(".msi"):
                result = self._run_elevated(
                    "msiexec",
                    f'/i "{setup_file}" /quiet /norestart TARGETDIR="{target_dir}"'
                )
                if not result.success and result.exit_code in self._DIR_PARAM_REJECTED_CODES:
                    result = self._run_elevated(
                        "msiexec", f'/i "{setup_file}" /quiet /norestart'
                    )
            else:
                installer_type = self._detect_installer_type(setup_file)
                clean_target = target_dir.rstrip("\\/")

                if installer_type == "innosetup":
                    result = self._run_elevated(
                        setup_file,
                        f'/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR="{clean_target}"'
                    )
                    if not result.success:
                        result = self._run_elevated(
                            setup_file, '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART'
                        )
                elif installer_type == "nsis":
                    result = self._run_elevated(setup_file, f'/S /D={clean_target}')
                    if not result.success and result.exit_code in self._DIR_PARAM_REJECTED_CODES:
                        result = self._run_elevated(setup_file, '/S')
                elif installer_type in ("installshield", "wix"):
                    # InstallShield: /s /v"/qn INSTALLDIR=\"<dir>\""
                    result = self._run_elevated(
                        setup_file,
                        f'/s /v"/qn INSTALLDIR=\\"{clean_target}\\""'
                    )
                    if not result.success and result.exit_code in self._DIR_PARAM_REJECTED_CODES:
                        result = self._run_elevated(setup_file, '/s /v/qn')
                else:
                    # Unknown — try InnoSetup first (most common), then NSIS, then InstallShield
                    result = self._run_elevated(
                        setup_file,
                        f'/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR="{clean_target}"'
                    )
                    if not result.success and result.exit_code in self._DIR_PARAM_REJECTED_CODES:
                        result = self._run_elevated(setup_file, f'/S /D={clean_target}')
                    if not result.success and result.exit_code in self._DIR_PARAM_REJECTED_CODES:
                        result = self._run_elevated(setup_file, '/s /v/qn')
                    if not result.success and result.exit_code in self._DIR_PARAM_REJECTED_CODES:
                        result = self._run_elevated(setup_file, '/S')

            return result
        except Exception as exc:
            return InstallResult(success=False, exit_code=-1, error=str(exc))

    @staticmethod
    def _detect_installer_type(exe_path: str) -> str:
        """Detect installer type using memory-mapped file scan."""
        import mmap
        try:
            with open(exe_path, "rb") as f:
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                    if mm.find(b"Inno Setup") != -1 or mm.find(b"InnoSetup") != -1:
                        return "innosetup"
                    if mm.find(b"Nullsoft") != -1 or mm.find(b"NSIS") != -1:
                        return "nsis"
                    if mm.find(b"InstallShield") != -1:
                        return "installshield"
                    if mm.find(b"WiX") != -1:
                        return "wix"
        except OSError:
            pass
        return "unknown"

    @staticmethod
    def _run_elevated(exe: str, params: str) -> InstallResult:
        """Launch exe with UAC elevation and wait for it to finish."""
        import ctypes
        import ctypes.wintypes

        SEE_MASK_NOCLOSEPROCESS = 0x00000040
        SW_HIDE = 0

        class SHELLEXECUTEINFOW(ctypes.Structure):
            _fields_ = [
                ("cbSize",         ctypes.wintypes.DWORD),
                ("fMask",          ctypes.wintypes.ULONG),
                ("hwnd",           ctypes.wintypes.HWND),
                ("lpVerb",         ctypes.wintypes.LPCWSTR),
                ("lpFile",         ctypes.wintypes.LPCWSTR),
                ("lpParameters",   ctypes.wintypes.LPCWSTR),
                ("lpDirectory",    ctypes.wintypes.LPCWSTR),
                ("nShow",          ctypes.c_int),
                ("hInstApp",       ctypes.wintypes.HINSTANCE),
                ("lpIDList",       ctypes.c_void_p),
                ("lpClass",        ctypes.wintypes.LPCWSTR),
                ("hkeyClass",      ctypes.wintypes.HKEY),
                ("dwHotKey",       ctypes.wintypes.DWORD),
                ("hIconOrMonitor", ctypes.wintypes.HANDLE),
                ("hProcess",       ctypes.wintypes.HANDLE),
            ]

        sei = SHELLEXECUTEINFOW()
        sei.cbSize = ctypes.sizeof(sei)
        sei.fMask = SEE_MASK_NOCLOSEPROCESS
        sei.lpVerb = "runas"
        sei.lpFile = exe
        sei.lpParameters = params
        sei.nShow = SW_HIDE

        ok = ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(sei))
        if not ok or not sei.hProcess:
            err = ctypes.GetLastError()
            return InstallResult(
                success=False, exit_code=-1,
                error=f"ShellExecuteEx failed (error {err})"
            )

        timeout_ms = 5 * 60 * 1000
        wait_result = ctypes.windll.kernel32.WaitForSingleObject(sei.hProcess, timeout_ms)

        exit_code = ctypes.wintypes.DWORD(0)
        ctypes.windll.kernel32.GetExitCodeProcess(sei.hProcess, ctypes.byref(exit_code))
        ctypes.windll.kernel32.CloseHandle(sei.hProcess)

        if wait_result == 0x00000102:  # WAIT_TIMEOUT
            return InstallResult(success=False, exit_code=-1, error="Timeout: installer chạy quá 5 phút")

        code = exit_code.value
        return InstallResult(success=code == 0, exit_code=code)


# ---------------------------------------------------------------------------
# InstallableRunner
# ---------------------------------------------------------------------------

class InstallableRunner:
    """Install into a managed directory, write a flag. Does NOT auto-launch."""

    def run(
        self,
        version: VersionInfo,
        app_name: str,
        on_status: callable = None,
    ) -> LaunchResult:
        # Vấn đề 2: collect ALL setup files, try each in order (exe first, then msi)
        setup_files = self._find_all_setup_files(version.path)
        if not setup_files:
            return LaunchResult(success=False, message="Không tìm thấy tệp cài đặt của phần mềm.")

        target = installed_dir(app_name, version.name)

        if on_status:
            on_status("Đang cài đặt...")

        # Snapshot Program Files BEFORE install to detect new exe after
        pf_before = _snapshot_program_files()

        # Try each setup file; stop on first success
        last_error = ""
        install_succeeded = False
        for setup_file in setup_files:
            result = SilentInstaller().install(setup_file, target)
            if result.success:
                install_succeeded = True
                break
            if result.exit_code == 1638:
                install_succeeded = True
                break
            last_error = result.error or f"Exit code: {result.exit_code}"

        if not install_succeeded:
            return LaunchResult(
                success=False,
                message=f"Cài đặt thất bại ({last_error}). Vui lòng thử lại.",
            )

        # Find the installed exe:
        # 1. Check managed target dir (works when installer respects /D=)
        # 2. Scan Program Files for new exe (most reliable for InstallShield)
        # 3. Registry snapshot diff as fallback
        # 4. Name-based search as last resort
        exe_path = _find_exe_in_dir(target)
        if not exe_path:
            exe_path = _find_new_exe_in_program_files(pf_before, app_name, version.name)
        if not exe_path:
            exe_path = (_find_via_registry(app_name)
                        or _find_via_registry(version.name)
                        or _find_in_program_files(app_name)
                        or _find_in_program_files(version.name))

        if not exe_path:
            return LaunchResult(
                success=False,
                message="Cài đặt hoàn tất nhưng không tìm thấy file thực thi trong thư mục cài đặt.",
            )

        # Write flag with exe path so next launch is instant
        try:
            flag_path = os.path.join(target, FLAG_FILE)
            with open(flag_path, "w", encoding="utf-8") as f:
                f.write(exe_path)
        except OSError:
            pass

        return LaunchResult(success=True, message=exe_path)

    @staticmethod
    def _find_all_setup_files(version_path: str) -> list[str]:
        """Return all setup files in version_path, .exe first then .msi."""
        try:
            entries = list(os.scandir(version_path))
        except (FileNotFoundError, NotADirectoryError, PermissionError):
            return []

        exe_files, msi_files = [], []
        for entry in sorted(entries, key=lambda e: e.name):
            if not entry.is_file():
                continue
            lower = entry.name.lower()
            if "setup" in lower:
                if lower.endswith(".exe"):
                    exe_files.append(entry.path)
                elif lower.endswith(".msi"):
                    msi_files.append(entry.path)

        return exe_files + msi_files  # exe tried first, msi as fallback


# ---------------------------------------------------------------------------
# SilentUninstaller
# ---------------------------------------------------------------------------

class SilentUninstaller:
    """Tìm uninstaller của app qua registry và chạy silent."""

    def uninstall(self, app_name: str, version_name: str) -> "LaunchResult":
        # 1. Tìm uninstall command trong registry (thử cả app_name lẫn version_name)
        uninstall_cmd = (self._find_uninstall_cmd(app_name)
                         or self._find_uninstall_cmd(version_name))
        if uninstall_cmd:
            cmd = self._fix_msi_uninstall_cmd(uninstall_cmd)
            result = self._run_uninstall(cmd)
            if result.success:
                clear_install_flag(app_name, version_name)
                return LaunchResult(success=True, message="Gỡ cài đặt thành công.")
            return LaunchResult(success=False,
                                message=f"Gỡ cài đặt thất bại (exit {result.exit_code}): {result.error}")

        # 2. Tìm uninstall.exe trong Program Files theo tên app
        uninst = (self._find_uninstaller_in_program_files(app_name)
                  or self._find_uninstaller_in_program_files(version_name))
        if uninst:
            result = self._run_uninstall(f'"{uninst}"')
            if result.success:
                clear_install_flag(app_name, version_name)
                return LaunchResult(success=True, message="Gỡ cài đặt thành công.")
            return LaunchResult(success=False,
                                message=f"Gỡ cài đặt thất bại (exit {result.exit_code}): {result.error}")

        # 3. Tìm uninstall.exe trong thư mục managed install
        idir = installed_dir(app_name, version_name)
        uninst = self._find_uninstaller_exe(idir)
        if uninst:
            result = self._run_uninstall(f'"{uninst}"')
            if result.success:
                clear_install_flag(app_name, version_name)
                return LaunchResult(success=True, message="Gỡ cài đặt thành công.")
            return LaunchResult(success=False,
                                message=f"Gỡ cài đặt thất bại (exit {result.exit_code}): {result.error}")

        # 4. Không tìm thấy uninstaller — báo lỗi rõ ràng, KHÔNG xóa flag
        return LaunchResult(
            success=False,
            message=(
                f"Không tìm thấy uninstaller cho '{app_name} - {version_name}'.\n"
                "Vui lòng gỡ cài đặt thủ công qua Control Panel > Programs and Features."
            ),
        )

    @staticmethod
    def _fix_msi_uninstall_cmd(cmd: str) -> str:
        """Đổi MsiExec /I{GUID} thành /X{GUID} /quiet /norestart."""
        import re
        # Pattern: MsiExec.exe /I{GUID} hoặc msiexec /i {GUID}
        fixed = re.sub(
            r'(?i)(msiexec(?:\.exe)?)\s+/[iI]\s*(\{[0-9A-Fa-f\-]+\})',
            r'\1 /X\2 /quiet /norestart',
            cmd,
        )
        return fixed

    @staticmethod
    def _find_uninstall_cmd(name: str) -> str | None:
        try:
            import winreg
        except ImportError:
            return None
        hives = [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]
        sub_keys = [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        ]
        name_words = [w.lower() for w in name.split() if len(w) > 1]
        for hive in hives:
            for sub_key in sub_keys:
                try:
                    with winreg.OpenKey(hive, sub_key) as key:
                        i = 0
                        while True:
                            try:
                                sub_name = winreg.EnumKey(key, i); i += 1
                            except OSError:
                                break
                            try:
                                with winreg.OpenKey(key, sub_name) as sub:
                                    def _val(n, _sub=sub):
                                        try:
                                            v, _ = winreg.QueryValueEx(_sub, n)
                                            return v if isinstance(v, str) else None
                                        except OSError:
                                            return None
                                    display = (_val("DisplayName") or "").lower()
                                    if not all(w in display for w in name_words):
                                        continue
                                    cmd = _val("QuietUninstallString") or _val("UninstallString")
                                    if cmd:
                                        return cmd
                            except OSError:
                                continue
                except OSError:
                    continue
        return None

    @staticmethod
    def _find_uninstaller_in_program_files(app_name: str) -> str | None:
        """Tìm uninstall.exe trong Program Files theo tên app."""
        roots = []
        for var in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
            p = os.environ.get(var)
            if p and os.path.isdir(p) and p not in roots:
                roots.append(p)
        name_lower = app_name.lower().replace(" ", "").replace("-", "")
        for root in roots:
            try:
                for entry in os.scandir(root):
                    if not entry.is_dir():
                        continue
                    dir_lower = entry.name.lower().replace(" ", "").replace("-", "")
                    # Kiểm tra tên thư mục khớp với app name (fuzzy)
                    if name_lower in dir_lower or dir_lower in name_lower:
                        uninst = SilentUninstaller._find_uninstaller_exe(entry.path)
                        if uninst:
                            return uninst
            except (PermissionError, OSError):
                continue
        return None

    @staticmethod
    def _find_uninstaller_exe(directory: str) -> str | None:
        """Tìm file uninstall*.exe trong thư mục."""
        try:
            for entry in sorted(os.scandir(directory), key=lambda e: e.name):
                if (entry.is_file()
                        and "uninstall" in entry.name.lower()
                        and entry.name.lower().endswith(".exe")):
                    return entry.path
        except (FileNotFoundError, NotADirectoryError, PermissionError):
            pass
        return None

    @staticmethod
    def _run_uninstall(cmd: str) -> "InstallResult":
        import ctypes
        import ctypes.wintypes

        cmd_lower = cmd.lower()
        # Thêm silent flags nếu chưa có (không thêm nếu đã có /quiet hoặc /x từ MSI fix)
        if "msiexec" in cmd_lower:
            if "/quiet" not in cmd_lower:
                cmd = cmd.rstrip() + " /quiet /norestart"
        elif "/verysilent" not in cmd_lower and "/s" not in cmd_lower.split():
            cmd = cmd.rstrip() + " /VERYSILENT /SUPPRESSMSGBOXES /NORESTART"

        # Tách exe và params
        cmd = cmd.strip()
        if cmd.startswith('"'):
            end = cmd.find('"', 1)
            exe = cmd[1:end]
            params = cmd[end + 1:].strip()
        else:
            parts = cmd.split(None, 1)
            exe = parts[0]
            params = parts[1] if len(parts) > 1 else ""

        SEE_MASK_NOCLOSEPROCESS = 0x00000040

        class SHELLEXECUTEINFOW(ctypes.Structure):
            _fields_ = [
                ("cbSize",         ctypes.wintypes.DWORD),
                ("fMask",          ctypes.wintypes.ULONG),
                ("hwnd",           ctypes.wintypes.HWND),
                ("lpVerb",         ctypes.wintypes.LPCWSTR),
                ("lpFile",         ctypes.wintypes.LPCWSTR),
                ("lpParameters",   ctypes.wintypes.LPCWSTR),
                ("lpDirectory",    ctypes.wintypes.LPCWSTR),
                ("nShow",          ctypes.c_int),
                ("hInstApp",       ctypes.wintypes.HINSTANCE),
                ("lpIDList",       ctypes.c_void_p),
                ("lpClass",        ctypes.wintypes.LPCWSTR),
                ("hkeyClass",      ctypes.wintypes.HKEY),
                ("dwHotKey",       ctypes.wintypes.DWORD),
                ("hIconOrMonitor", ctypes.wintypes.HANDLE),
                ("hProcess",       ctypes.wintypes.HANDLE),
            ]

        sei = SHELLEXECUTEINFOW()
        sei.cbSize = ctypes.sizeof(sei)
        sei.fMask = SEE_MASK_NOCLOSEPROCESS
        sei.lpVerb = "runas"
        sei.lpFile = exe
        sei.lpParameters = params or None
        sei.nShow = 0  # SW_HIDE

        ok = ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(sei))
        if not ok or not sei.hProcess:
            err = ctypes.GetLastError()
            return InstallResult(success=False, exit_code=-1,
                                 error=f"ShellExecuteEx failed (error {err})")

        timeout_ms = 5 * 60 * 1000
        ctypes.windll.kernel32.WaitForSingleObject(sei.hProcess, timeout_ms)
        exit_code = ctypes.wintypes.DWORD(0)
        ctypes.windll.kernel32.GetExitCodeProcess(sei.hProcess, ctypes.byref(exit_code))
        ctypes.windll.kernel32.CloseHandle(sei.hProcess)
        code = exit_code.value
        return InstallResult(success=code in (0, 3010), exit_code=code,
                             error="" if code in (0, 3010) else f"exit code {code}")


# ---------------------------------------------------------------------------
# AppLauncher
# ---------------------------------------------------------------------------

class AppLauncher:
    """Orchestrate PortableRunner and InstallableRunner based on AppType."""

    def launch(
        self,
        version: VersionInfo,
        app_name: str = "",
        on_status: callable = None,
    ) -> LaunchResult:
        if version.app_type == AppType.PORTABLE:
            return PortableRunner().run(version.path)

        # Check if already installed — launch directly
        exe = is_installed(app_name, version.name)
        if exe:
            return _launch_exe(exe)

        return InstallableRunner().run(version, app_name, on_status)
