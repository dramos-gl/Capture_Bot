"""
playwright_setup.py
-------------------
Módulo centralizado para resolver el ejecutable de Chromium cuando la aplicación
se ejecuta como un ejecutable PyInstaller congelado (frozen).

Problema raíz:
  PyInstaller incluye el *driver* de Playwright pero NO descarga los navegadores.
  Al ejecutar en el equipo cliente, Playwright falla con:
    "BrowserType.launch: Executable doesn't exist at ..._internal\\...\\chrome.exe"

Estrategia de resolución (en orden de prioridad):
  1. Si el navegador bundled de Playwright existe → usarlo directamente (dev normal).
  2. Si se ejecuta frozen y el navegador NO existe → intentar auto-instalar via
     "playwright install chromium" usando el driver que sí viene bundled.
  3. Si el navegador instalado por el usuario existe en rutas de sistema
     (Chrome / Edge) → usar executable_path apuntando al navegador del sistema.
  4. Si nada funciona → lanzar un error descriptivo con instrucciones claras.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _is_frozen() -> bool:
    """Returns True when running as a PyInstaller frozen executable."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def _get_playwright_driver_dir() -> Optional[Path]:
    """
    Returns the Playwright driver directory bundled inside the frozen executable,
    or None if not running frozen.
    """
    if not _is_frozen():
        return None
    # PyInstaller unpacks _internal next to the .exe (or into sys._MEIPASS)
    base = Path(sys._MEIPASS)
    # Playwright bundles its driver at: playwright/driver/
    driver = base / "playwright" / "driver"
    return driver if driver.exists() else None


def _get_playwright_chromium_path() -> Optional[Path]:
    """
    Locates the Playwright-managed Chromium executable.
    Works both in normal (dev) and frozen (PyInstaller) modes.
    """
    # In frozen mode, check inside _internal
    if _is_frozen():
        base = Path(sys._MEIPASS)
        # Playwright stores browsers under .local-browsers/
        browsers_root = base / "playwright" / "driver" / "package" / ".local-browsers"
        if browsers_root.exists():
            for chromium_dir in browsers_root.glob("chromium-*"):
                chrome_exe = chromium_dir / "chrome-win64" / "chrome.exe"
                if chrome_exe.exists():
                    logger.info(f"[PlaywrightSetup] Chromium bundled encontrado: {chrome_exe}")
                    return chrome_exe
        return None

    # In dev mode, use the default Playwright location
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as pw:
            # Playwright exposes the default executable path via the browser object
            # We query it without launching
            executable = Path(pw.chromium.executable_path)
            if executable.exists():
                return executable
    except Exception:
        pass
    return None


def _get_system_chrome_path() -> Optional[Path]:
    """
    Returns the path to a system-installed Chromium-based browser (Chrome or Edge).
    Checked in common Windows installation paths.
    """
    candidates = [
        # Google Chrome (stable, beta, dev)
        Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        # Microsoft Edge (Chromium-based)
        Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
    ]
    for path in candidates:
        if path.exists():
            logger.info(f"[PlaywrightSetup] Navegador del sistema encontrado: {path}")
            return path
    return None


def _try_install_playwright_browsers(progress_callback=None) -> bool:
    """
    Attempts to install Playwright browsers using the bundled driver.
    Returns True if successful.
    
    Args:
        progress_callback: Optional callable(str) to report progress to UI.
    """
    def _report(msg: str):
        logger.info(f"[PlaywrightSetup] {msg}")
        if progress_callback:
            progress_callback(msg)

    if _is_frozen():
        driver_dir = _get_playwright_driver_dir()
        if not driver_dir:
            _report("No se encontró el driver de Playwright bundled.")
            return False

        # The Playwright node binary inside the bundle
        playwright_node = driver_dir / "playwright.cmd"
        if not playwright_node.exists():
            playwright_node = driver_dir / "playwright"

        if playwright_node.exists():
            _report("Instalando navegador Chromium (primera ejecución, puede tomar unos minutos)...")
            try:
                result = subprocess.run(
                    [str(playwright_node), "install", "chromium"],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minutes max
                )
                if result.returncode == 0:
                    _report("Chromium instalado correctamente.")
                    return True
                else:
                    _report(f"Error instalando Chromium: {result.stderr[:300]}")
                    return False
            except subprocess.TimeoutExpired:
                _report("Timeout instalando Chromium.")
                return False
            except Exception as e:
                _report(f"Excepción instalando Chromium: {e}")
                return False
    else:
        # Dev mode: run `playwright install chromium` via Python
        _report("Instalando navegadores Playwright (modo desarrollo)...")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode == 0:
                _report("Chromium instalado correctamente.")
                return True
            _report(f"Error: {result.stderr[:300]}")
            return False
        except Exception as e:
            _report(f"Excepción: {e}")
            return False


def resolve_chromium_executable(progress_callback=None) -> Optional[str]:
    """
    Master resolution function. Returns the path to use as `executable_path`
    in playwright.chromium.launch(), or None to use Playwright's default
    (which implies the browser is already available).

    Resolution order:
      1. Playwright-managed Chromium exists → return None (use default).
      2. Frozen + no browser → try auto-install → if succeeds, return None.
      3. System Chrome/Edge → return its path.
      4. All fails → raise RuntimeError with clear user instructions.

    Args:
        progress_callback: Optional callable(str) to forward status messages to UI.
    """
    def _report(msg: str):
        logger.info(f"[PlaywrightSetup] {msg}")
        if progress_callback:
            progress_callback(msg)

    # Step 1: Check if Playwright's own Chromium is already present
    pw_path = _get_playwright_chromium_path()
    if pw_path:
        _report(f"Chromium Playwright disponible: {pw_path.name}")
        return None  # Use Playwright default resolution

    _report("Chromium de Playwright no encontrado. Buscando alternativas...")

    # Step 2: If frozen, try auto-install
    if _is_frozen():
        _report("Modo ejecutable detectado. Intentando instalar Chromium automáticamente...")
        installed = _try_install_playwright_browsers(progress_callback)
        if installed:
            # After install, check again
            pw_path = _get_playwright_chromium_path()
            if pw_path:
                return None

    # Step 3: Fall back to system Chrome/Edge
    sys_path = _get_system_chrome_path()
    if sys_path:
        _report(f"Usando navegador del sistema: {sys_path.name}")
        return str(sys_path)

    # Step 4: All failed — provide a clear error
    msg = (
        "No se encontró un navegador compatible para ejecutar el bot.\n\n"
        "Solución:\n"
        "  1. Instale Google Chrome o Microsoft Edge en este equipo, ó\n"
        "  2. Ejecute el siguiente comando en una terminal:\n"
        "       playwright install chromium\n\n"
        "Ruta esperada del ejecutable:\n"
        f"  {_get_playwright_driver_dir() or 'N/A'}"
    )
    logger.error(f"[PlaywrightSetup] {msg}")
    raise RuntimeError(msg)
