#!/usr/bin/env python3
import os
import shutil
import argparse
from pathlib import Path
import logging
import sys
import random

"""
script.py - Automatically sort files by type.

Usage:
    python script.py [--path PATH] [--dest DEST] [--recursive] [--dry-run] [--copy] [--extract] [--pretest] [--remove-empty] [--trash]

Options:
    --path PATH      Source directory (default: current directory)
    --dest DEST      Directory where sorted folders will be created (default: same as --path)
    --recursive      Sort recursively into subfolders
    --dry-run        Simulate without moving files
    --copy           Copy instead of move
    --extract        Extract archives (zip/tar/...) into their destination folder
    --pretest        Create a bunch of unsorted files in --path and exit
    --remove-empty   Remove empty subdirectories after sorting (respect --dry-run)
    --trash          If provided, delete directories permanently. Otherwise move empty dirs to a .trashcan folder
"""


# Mapping of extensions to folders (lowercase)
EXTENSION_MAP = {
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".svg", ".webp"],
    "Videos": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"],
    "Music": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"],
    "Documents": [
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".txt",
        ".odt",
        ".rtf",
    ],
    "Archives": [".zip", ".tar", ".gz", ".bz2", ".7z", ".rar"],
    "Code": [
        ".py",
        ".js",
        ".ts",
        ".java",
        ".c",
        ".cpp",
        ".cs",
        ".html",
        ".css",
        ".json",
        ".xml",
        ".sh",
    ],
    "Fonts": [".ttf", ".otf", ".woff", ".woff2"],
}

DEFAULT_CATEGORY = "Others"

logging.basicConfig(format="%(message)s", level=logging.INFO)


def get_category(ext: str) -> str:
    """The function `get_category` takes a file extension as input and returns the corresponding category based on a predefined mapping.

    Args:
        ext (str): The file extension to categorize.

    Returns:
        out (str): The function `get_category` is returning a string value, which is the category corresponding to the given file extension. If the file extension is found in the `EXTENSION_MAP`, the function returns the category associated with that extension. If the extension is not found in the map, it returns the `DEFAULT_CATEGORY`.
    """
    ext = ext.lower()
    for category, exts in EXTENSION_MAP.items():
        if ext in exts:
            return category
    return DEFAULT_CATEGORY


def unique_target_path(dest: Path) -> Path:
    """The function `unique_target_path` generates a unique path by appending a numerical suffix to the stem of the input path if the original path already exists.

    Args:
        dest (Path): The `unique_target_path` function takes a `Path` object as input, which represents the destination path where a file is to be saved. The function generates a unique target path by appending a numerical suffix to the file name if a file with the same name already exists at the destination.

    Returns:
        out (Path): The function `unique_target_path` is returning a unique path by appending a numerical suffix to the stem of the original path if the original path already exists.
    """
    if not dest.exists():
        return dest
    stem = dest.stem
    parent = dest.parent
    suffix = dest.suffix
    i = 1
    while True:
        candidate = parent / f"{stem}_{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def move_or_copy(src: Path, dest: Path, copy: bool, dry_run: bool):
    """The function `move_or_copy` takes a source and destination path, along with flags for copying or moving the file, and performs the specified action while logging the operation, with an option for a dry run.

    Args:
        src (Path): The `src` parameter represents the source file or directory that you want to either move or copy.

        dest (Path): The `dest` parameter represents the destination path where the file or directory will be moved or copied to.

        copy (bool): The `copy` parameter in the `move_or_copy` function is a boolean flag that determines whether the file should be copied (`True`) or moved (`False`) from the source path (`src`) to the destination path (`dest`). If `copy` is `True`, the function will copy the file; if `copy` is `False`, it will move the file.

        dry_run (bool): The `dry_run` parameter is a boolean flag that, when set to `True`, indicates that the function should only simulate the action (copy or move) without actually performing it. This is useful for previewing what would happen without making any changes to the file system.

    Returns:
        out: If the `dry_run` flag is set to `True`, the function will log a message indicating whether the action is a copy or move operation in a dry run scenario. In this case, the function will return without performing any actual file operations.
    """
    if dry_run:
        action = "COPY" if copy else "MOVE"
        logging.info(f"[DRY] {action}: {src} -> {dest}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest = unique_target_path(dest)
    try:
        if copy:
            shutil.copy2(src, dest)
        else:
            shutil.move(str(src), str(dest))
        logging.info(f"{'COPIED' if copy else 'MOVED'}: {src} -> {dest}")
    except Exception as e:
        action = "copying" if copy else "moving"
        logging.error(f"Error while {action} {src} -> {dest}: {e}")


def handle_archive(src: Path, extract: bool, target_folder: Path, dry_run: bool):
    """The function `handle_archive` extracts or moves/copies an archive file based on the specified parameters.

    Args:
        src (Path): The `src` parameter represents the path to the archive file that you want to handle.

        extract (bool): The `extract` parameter in the `handle_archive` function is a boolean flag that determines whether to unpack the archive into the target folder or just move/copy the archive without extracting it. If `extract` is set to `True`, the function will attempt to unpack the archive into a subfolder.

        target_folder (Path): The `target_folder` parameter in the `handle_archive` function represents the directory where the archive will be extracted or moved/copied to, depending on the value of the `extract` parameter.

        dry_run (bool): The `dry_run` parameter is a boolean flag that indicates whether the function should perform the actual extraction or just simulate it without making any changes. If `dry_run` is set to `True`, the function will log the extraction actions that would have been taken without actually executing them. This is useful

    Returns:
        out (bool): The function `handle_archive` returns a boolean value. If the `extract` parameter is set to `False`, the function returns `False`. If the extraction is successful (i.e., the archive is unpacked into the target folder), the function returns `True`. If there is an unsupported archive format, a corrupted archive, or any other exception occurs during the extraction process, the function returns `False`.
    """

    """
    If extract=True, try to unpack the archive into target_folder/archive_name/
    Otherwise, just move/copy the archive.
    """
    if not extract:
        return False
    # Create a folder per archive (without extension)
    name = src.stem
    extract_dir = target_folder / name
    if dry_run:
        logging.info(f"[DRY] EXTRACT: {src} -> {extract_dir}")
        return True
    extract_dir.mkdir(parents=True, exist_ok=True)
    try:
        shutil.unpack_archive(str(src), str(extract_dir))
        logging.info(f"EXTRACTED: {src} -> {extract_dir}")
        return True
    except shutil.ReadError:
        logging.warning(f"Unsupported archive format or corrupted archive: {src}")
        return False
    except Exception as e:
        logging.error(f"Error extracting {src}: {e}")
        return False


def prune_empty_dirs(src: Path, output_dirs: set, dry_run: bool, trash_permanent: bool, trash_dir: Path):
    """Remove or move empty directories under src.

    Args:
        src (Path): The `src` parameter is a `Path` object that represents the source directory from which empty directories will be pruned.
        output_dirs (set): A set of directories that should be skipped when pruning empty directories. These directories are typically the output directories where sorted files are stored.
        
        dry_run (bool): The `dry_run` parameter is a boolean flag that indicates whether the function should perform a dry run or not. If `dry_run` is set to `True`, the function will only log the actions it would take without actually performing any file operations.
        
        trash_permanent (bool): The `trash_permanent` parameter is a boolean flag that determines whether empty directories should be permanently deleted or moved to a trash directory. If `trash_permanent` is set to `True`, the empty directories will be permanently removed using `os.rmdir()`. If it is set to `False`, the empty directories will be moved to the specified `trash_dir`.
        
        trash_dir (Path): The `trash_dir` parameter is a `Path` object that represents the directory where empty directories will be moved if they are not being permanently deleted. This directory is used when the `trash_permanent` parameter is set to `False`. The function will create this directory if it does not already exist.
    """
    src = src.resolve()
    trash_dir = trash_dir.resolve()

    # Walk bottom-up to remove deepest empty dirs first
    for root, dirs, files in os.walk(src, topdown=False):
        p = Path(root).resolve()

        # Skip the source root itself
        if p == src:
            continue

        # Skip output directories and their parents
        skip = False
        try:
            for out in output_dirs:
                # If this folder is the output folder or inside it, skip
                if p == out or out in p.parents or p == out:
                    skip = True
                    break
            if trash_dir in p.parents or p == trash_dir:
                skip = True
        except Exception:
            # permission issues - skip
            skip = True

        if skip:
            continue

        # Ignore symlinks
        try:
            if p.is_symlink():
                continue
        except Exception:
            continue

        # If directory is empty (no files and no dirs), remove or move it
        try:
            is_empty = True
            for _ in p.iterdir():
                is_empty = False
                break
        except Exception:
            # Can't read dir; skip
            continue

        if not is_empty:
            continue

        # Prepare action
        if dry_run:
            if trash_permanent:
                logging.info(f"[DRY] REMOVE EMPTY DIR: {p}")
            else:
                logging.info(f"[DRY] MOVE EMPTY DIR TO TRASH: {p} -> {trash_dir}")
            continue

        # Perform action
        if trash_permanent:
            try:
                os.rmdir(str(p))
                logging.info(f"REMOVED EMPTY DIR: {p}")
            except Exception as e:
                logging.error(f"Error removing dir {p}: {e}")
        else:
            try:
                # ensure trash_dir exists
                trash_dir.mkdir(parents=True, exist_ok=True)
                dest = unique_target_path(trash_dir / p.name)
                shutil.move(str(p), str(dest))
                logging.info(f"MOVED EMPTY DIR TO TRASH: {p} -> {dest}")
            except Exception as e:
                logging.error(f"Error moving dir {p} to trash {trash_dir}: {e}")


def should_skip(path: Path, output_dirs: set) -> bool:
    """The function `should_skip` determines whether a given file path should be skipped based on whether it is inside specified output directories.

    Args:
        path (Path): The `path` parameter is a file path that you want to check for skipping based on certain conditions

        output_dirs (set): A set containing directories where output files are stored

    Returns:
        out (bool): The function `should_skip` returns a boolean value - `True` if the file path is inside one of the output directories or equal to one of the output directories, and `False` otherwise.
    """
    # Do not process folders intended for sorting
    for p in path.resolve().parents:
        pass
    # Skip if the file is inside one of the output dirs
    try:
        for out in output_dirs:
            if out in path.resolve().parents or path.resolve() == out:
                return True
    except Exception:
        # in case of permission error, etc.
        return False
    return False


def collect_files(src: Path, recursive: bool, output_dirs: set):
    """The function `collect_files` iterates through files in a directory, optionally recursively,
    excluding specified output directories.

    Args:
        src (Path): The `src` parameter is expected to be a `Path` object representing the directory from which files are to be collected
        
        recursive (bool): The `recursive` parameter is a boolean flag that determines whether the file collection should be done recursively or not. If `recursive` is set to `True`, the function will search for files not only in the specified source directory (`src`) but also in all subdirectories.
        
        output_dirs (set): The `output_dirs` parameter is a set that contains directories that should be skipped when collecting files. If a file is found within one of the directories listed in `output_dirs`, it should not be included in the output
    """
    if recursive:
        for p in src.rglob("*"):
            if p.is_file() and not should_skip(p, output_dirs):
                yield p
    else:
        for p in src.iterdir():
            if p.is_file() and not should_skip(p, output_dirs):
                yield p


def pretest(src: Path):
    """Create a bunche of unsorted files for testing. Create sometimes subfolders.

    Args:
        src (Path): The `src` parameter is a `Path` object that represents the directory where the unsorted test files will be created.
    """
    test_files = {
        "image1.jpg": b"\xff\xd8\xff\xe0" + os.urandom(1024),
        "video1.mp4": b"\x00\x00\x00\x18ftypmp42" + os.urandom(2048),
        "document1.pdf": b"%PDF-" + os.urandom(512),
        "music1.mp3": b"ID3" + os.urandom(1024),
        "archive1.zip": b"PK\x03\x04" + os.urandom(1024),
        "script1.py": b"print('Hello, World!')" + os.urandom(256),
        "font1.ttf": b"\x00\x01\x00\x00" + os.urandom(512),
        "unknown.xyz": os.urandom(128),
    }
    for filename, content in test_files.items():
        # Randomly decide to put some files in subfolders
        if random.choice([True, False]):
            subfolder = src / f"subfolder_{random.randint(1,3)}"
            subfolder.mkdir(parents=True, exist_ok=True)
            file_path = subfolder / filename
        else:
            file_path = src / filename
        with open(file_path, "wb") as f:
            f.write(content)
    logging.info(f"Pretest files created in {src}")


def main():
    parser = argparse.ArgumentParser(description="Automatically sort files by type")
    parser.add_argument("--path", "-p", type=str, default=".", help="Source directory")
    parser.add_argument(
        "--dest",
        "-d",
        type=str,
        default=None,
        help="Destination directory (default = same as --path)",
    )
    parser.add_argument(
        "--recursive", "-r", action="store_true", help="Sort recursively"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Simulate without moving"
    )
    parser.add_argument("--copy", action="store_true", help="Copy instead of move")
    parser.add_argument(
        "--extract", action="store_true", help="Extract archives into their folder"
    )
    parser.add_argument(
        "--pretest", action="store_true", help="Create pretest files in --path and exit"
    )
    parser.add_argument(
        "--remove-empty",
        action="store_true",
        help="Remove empty subdirectories after sorting (respect --dry-run)",
    )
    parser.add_argument(
        "--trash",
        action="store_true",
        help="If provided, delete directories permanently. Otherwise move empty dirs to a .trashcan folder",
    )

    args = parser.parse_args()

    src = Path(args.path).expanduser().resolve()

    # If pretest requested, ensure source exists, create test files and quit
    if args.pretest:
        src.mkdir(parents=True, exist_ok=True)
        pretest(src)
        sys.exit(0)

    if not src.exists() or not src.is_dir():
        logging.error(f"Path not found or not a directory: {src}")
        sys.exit(1)

    dest_base = Path(args.dest).expanduser().resolve() if args.dest else src
    if not args.dry_run:
        dest_base.mkdir(parents=True, exist_ok=True)

    # Pre-create destination folders to avoid walking into them
    output_dirs = set()
    for category in list(EXTENSION_MAP.keys()) + [DEFAULT_CATEGORY]:
        d = dest_base / category
        output_dirs.add(d.resolve())
        if not args.dry_run:
            d.mkdir(parents=True, exist_ok=True)

    # Iterate and process files
    for file_path in collect_files(src, args.recursive, output_dirs):
        ext = file_path.suffix.lower()
        category = get_category(ext)
        target_folder = dest_base / category
        target = target_folder / file_path.name

        # If archive and extract option enabled, try extraction
        if category == "Archives" and args.extract:
            # Move or copy the archive first, then extract into a folder
            if args.copy:
                # Copy archive to target, then extract the copy
                move_or_copy(file_path, target, copy=True, dry_run=args.dry_run)
                copied = target
                if not args.dry_run:
                    handle_archive(
                        copied,
                        extract=True,
                        target_folder=target_folder,
                        dry_run=args.dry_run,
                    )
            else:
                # Move the archive then extract
                move_or_copy(file_path, target, copy=False, dry_run=args.dry_run)
                moved = target
                if not args.dry_run:
                    handle_archive(
                        moved,
                        extract=True,
                        target_folder=target_folder,
                        dry_run=args.dry_run,
                    )
            continue

        # General case: move or copy
        move_or_copy(file_path, target, copy=args.copy, dry_run=args.dry_run)

    # Optionally prune empty directories
    if args.remove_empty:
        # Decide trash behavior: if --trash then permanent deletion, else move to .trashcan
        trash_permanent = bool(args.trash)
        # Default trash dir is a hidden folder at src/.trashcan
        trash_dir = src / ".trashcan"
        prune_empty_dirs(src, output_dirs, dry_run=bool(args.dry_run), trash_permanent=trash_permanent, trash_dir=trash_dir)


if __name__ == "__main__":
    main()
