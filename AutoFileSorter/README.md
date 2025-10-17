# AutoFileSorter

**Language:** Python  
**Level:** Beginner / Intermediate  
**Purpose:** Automatically sort files in a folder by type and organize them into subfolders.

## Description

AutoFileSorter is a Python script that helps **save time and stay organized** by automatically sorting files such as images, videos, documents, etc.  
It is suitable for personal use or small businesses needing simple file organization.

## Features

- Automatically sorts files by extension  
- Creates subfolders as needed  
- Logs sorted files  
- Allows customization of file types and folders  

## Installation

1. Clone the Portfolio repository:

```bash
git clone https://github.com/Mathéo-Petry/Portfolio.git
```

2. Navigate to the project folder:

```bash
cd Portfolio/AutoFileSorter
```

## Usage

Run the script with the following command:

```bash
python3 script.py [options]
```

### Options

- `--path`: Path to the folder to be sorted. (Default: current directory)
- `--dest`: Directory where sorted folders will be created. (Default: same as --path)
- `--recursive`: Sort recursively into subfolders.
- `--dry-run`: Simulate without moving files.
- `--copy`: Copy instead of move.
- `--extract`: Extract archives (zip/tar/...) into their destination folder.
- `--pretest`: Create a bunch of unsorted files in --path and exit.
- `--remove-empty`: Remove empty subdirectories after sorting (respect --dry-run).
- `--trash`: If provided, delete directories permanently. Otherwise move empty dirs to a .trashcan folder.
