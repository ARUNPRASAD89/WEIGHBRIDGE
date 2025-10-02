import os
import shutil
import sys
from typing import Optional, List

# Robust import of resource_path.resource_path:
# - Prefer a normal import so static analyzers / PyInstaller pick it up.
# - If that fails, attempt to load resource_path.py from the same directory.
try:
    from resource_path import resource_path
except Exception:
    import importlib.util
    _this_dir = os.path.dirname(os.path.abspath(__file__))
    _rp_path = os.path.join(_this_dir, "resource_path.py")
    if os.path.exists(_rp_path):
        spec = importlib.util.spec_from_file_location("resource_path", _rp_path)
        _rp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_rp)  # type: ignore
        resource_path = getattr(_rp, "resource_path")
    else:
        raise ModuleNotFoundError(
            "Could not import 'resource_path'. Place resource_path.py next to resource_helpers.py "
            f"({_rp_path}) or make it importable on sys.path."
        )

APP_NAME = "Weighbridge"
USER_SUBFOLDERS = {
    "vehicle_images": "vehicle_images",
    "print_templates": "print_templates",
    "print_jobs": "print_jobs",
}


def user_app_root() -> str:
    """Return the user-writable root folder for the app (LOCALAPPDATA\\Weighbridge)."""
    appdata = os.getenv("LOCALAPPDATA") or os.path.expanduser("~\\AppData\\Local")
    root = os.path.join(appdata, APP_NAME)
    os.makedirs(root, exist_ok=True)
    return root


def user_folder(folder_key: str) -> str:
    """Return full path to a named subfolder under the user app root."""
    if folder_key not in USER_SUBFOLDERS:
        raise ValueError(f"Unknown folder key: {folder_key}")
    path = os.path.join(user_app_root(), USER_SUBFOLDERS[folder_key])
    os.makedirs(path, exist_ok=True)
    return path


def bundled_folder_path(folder_key: str) -> Optional[str]:
    """Return the path to the bundled folder when running from source or PyInstaller."""
    try:
        candidate = resource_path(USER_SUBFOLDERS[folder_key])
        if os.path.exists(candidate) and os.path.isdir(candidate):
            return candidate
    except Exception:
        pass
    return None


def list_bundled_files(folder_key: str) -> List[str]:
    """Return list of filenames inside the bundled folder (basename list)."""
    bp = bundled_folder_path(folder_key)
    if not bp:
        return []
    return [f for f in os.listdir(bp) if os.path.isfile(os.path.join(bp, f))]


def resolve_resource(db_value: Optional[str], folder_key: str) -> Optional[str]:
    """
    Resolve a DB-stored value to an absolute filesystem path.

    Resolution order:
      1) If db_value is absolute and exists -> return it.
      2) If basename exists in the user folder -> return that.
      3) If basename exists in the bundled folder -> return that.
      4) Otherwise return None.
    """
    if not db_value:
        return None

    val = str(db_value).strip()

    # 1) absolute path
    try:
        if os.path.isabs(val) and os.path.exists(val):
            return os.path.normpath(val)
    except Exception:
        pass

    basename = os.path.basename(val)

    # 2) user folder
    try:
        user_candidate = os.path.join(user_folder(folder_key), basename)
        if os.path.exists(user_candidate):
            return user_candidate
    except Exception:
        pass

    # 3) bundled folder
    try:
        bundled = bundled_folder_path(folder_key)
        if bundled:
            bundled_candidate = os.path.join(bundled, basename)
            if os.path.exists(bundled_candidate):
                return bundled_candidate
    except Exception:
        pass

    return None


def save_user_file(source_path: str, folder_key: str, dest_basename: Optional[str] = None) -> str:
    """
    Copy a source file into the user folder and return the basename to store in DB.
    """
    if not os.path.exists(source_path):
        raise FileNotFoundError(source_path)
    _, ext = os.path.splitext(source_path)
    if not dest_basename:
        dest_basename = os.path.basename(source_path)
    dest_basename = "".join(c for c in dest_basename if c.isalnum() or c in (" ", "_", "-", ".")).strip()
    if not os.path.splitext(dest_basename)[1]:
        dest_basename = dest_basename + ext
    dest = os.path.join(user_folder(folder_key), dest_basename)
    shutil.copy2(source_path, dest)
    return dest_basename


def seed_bundled_to_user(folder_key: str, overwrite: bool = False) -> int:
    """
    Copy bundled files into the user folder if missing. Returns number copied.
    """
    bundled = bundled_folder_path(folder_key)
    if not bundled:
        return 0
    userdir = user_folder(folder_key)
    copied = 0
    for fn in os.listdir(bundled):
        src = os.path.join(bundled, fn)
        if not os.path.isfile(src):
            continue
        dst = os.path.join(userdir, fn)
        if not os.path.exists(dst) or overwrite:
            try:
                shutil.copy2(src, dst)
                copied += 1
            except Exception:
                pass
    return copied


def get_print_template_path(template_basename: str) -> Optional[str]:
    return resolve_resource(template_basename, "print_templates")


def ensure_print_job_file(path_or_basename: str) -> Optional[str]:
    return resolve_resource(path_or_basename, "print_jobs")


def debug_candidates(db_value: str, folder_key: str) -> List[str]:
    """
    Return list of candidate paths the resolver would try (useful for debugging).
    """
    candidates: List[str] = []
    try:
        if os.path.isabs(db_value):
            candidates.append(os.path.normpath(db_value))
    except Exception:
        pass
    basename = os.path.basename(db_value)
    try:
        candidates.append(os.path.join(user_folder(folder_key), basename))
    except Exception:
        pass
    bundled = bundled_folder_path(folder_key)
    if bundled:
        candidates.append(os.path.join(bundled, basename))
    return candidates
