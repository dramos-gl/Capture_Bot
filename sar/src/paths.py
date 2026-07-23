"""Global paths definition for the SAR system."""
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_settings_path() -> str:
    """Resolves the settings.json file path robustly in both dev and production."""
    # 1. If running as compiled PyInstaller executable
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        # Try moving up from dist/SAR_Servidor/ or dist/SAR_Cliente/ to C:/SAR_System/sar/settings.json
        candidate = os.path.abspath(os.path.join(exe_dir, "..", "..", "sar", "settings.json"))
        if os.path.exists(candidate):
            return candidate
        # Try next to the executable
        candidate_exe = os.path.abspath(os.path.join(exe_dir, "settings.json"))
        if os.path.exists(candidate_exe):
            return candidate_exe

    # 2. Default dev path (C:/SAR_System/sar/settings.json)
    candidate_dev = os.path.abspath(os.path.join(BASE_DIR, "settings.json"))
    if os.path.exists(candidate_dev):
        return candidate_dev
        
    # 3. Check current working directory
    candidate_cwd = os.path.abspath("settings.json")
    if os.path.exists(candidate_cwd):
        return candidate_cwd

    return candidate_dev
