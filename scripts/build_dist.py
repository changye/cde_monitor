from __future__ import annotations

from pathlib import Path
import shutil
import zipfile


ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist"
PACKAGE_ROOT = DIST_DIR / "package" / "cde-monitor"
RUNTIME_ROOT = DIST_DIR / "runtime-package" / "cde-monitor"

CACHE_DIR_NAMES = {"__pycache__", ".pytest_cache"}
CACHE_FILE_SUFFIXES = {".pyc", ".pyo"}
EXCLUDED_BUNDLE_NAMES = {"build_dist.py"}


def remove_local_caches(root: Path) -> None:
    for path in root.rglob("*"):
        if path.is_dir() and path.name in CACHE_DIR_NAMES:
            shutil.rmtree(path, ignore_errors=True)
        elif path.is_file() and path.suffix in CACHE_FILE_SUFFIXES:
            path.unlink(missing_ok=True)


def copy_tree_clean(source: Path, destination: Path) -> None:
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns(
            "__pycache__",
            "*.pyc",
            "*.pyo",
            ".pytest_cache",
            *EXCLUDED_BUNDLE_NAMES,
        ),
        dirs_exist_ok=True,
    )


def reset_dist() -> None:
    shutil.rmtree(DIST_DIR / "package", ignore_errors=True)
    shutil.rmtree(DIST_DIR / "runtime-package", ignore_errors=True)
    (DIST_DIR / "cde-monitor.zip").unlink(missing_ok=True)
    (DIST_DIR / "cde-monitor-runtime.zip").unlink(missing_ok=True)
    PACKAGE_ROOT.mkdir(parents=True, exist_ok=True)
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)


def copy_package_contents() -> None:
    shutil.copy2(ROOT / "SKILL.md", PACKAGE_ROOT / "SKILL.md")
    shutil.copy2(ROOT / ".clawhubignore", PACKAGE_ROOT / ".clawhubignore")
    copy_tree_clean(ROOT / "scripts", PACKAGE_ROOT / "scripts")
    copy_tree_clean(ROOT / "references", PACKAGE_ROOT / "references")
    copy_tree_clean(ROOT / "tests", PACKAGE_ROOT / "tests")


def copy_runtime_contents() -> None:
    shutil.copy2(ROOT / "SKILL.md", RUNTIME_ROOT / "SKILL.md")
    copy_tree_clean(ROOT / "scripts", RUNTIME_ROOT / "scripts")
    copy_tree_clean(ROOT / "references", RUNTIME_ROOT / "references")


def create_zip(source_root: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_root.rglob("*")):
            if path.is_dir():
                continue
            archive.write(path, path.relative_to(source_root.parent))


def main() -> int:
    remove_local_caches(ROOT / "scripts")
    remove_local_caches(ROOT / "tests")
    reset_dist()
    copy_package_contents()
    copy_runtime_contents()
    create_zip(PACKAGE_ROOT, DIST_DIR / "cde-monitor.zip")
    create_zip(RUNTIME_ROOT, DIST_DIR / "cde-monitor-runtime.zip")

    print("Built dist artifacts:")
    for path in [
        DIST_DIR / "package",
        DIST_DIR / "runtime-package",
        DIST_DIR / "cde-monitor.zip",
        DIST_DIR / "cde-monitor-runtime.zip",
    ]:
        print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())