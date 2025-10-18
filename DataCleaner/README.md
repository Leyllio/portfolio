# DataCleaner

**Language:** Python (pandas)  
**Purpose:** Automatically clean and format CSV files.

## Description

DataCleaner allows you to quickly process CSV files: remove duplicates, handle missing values, and export a clean file.

## Features

- Remove duplicates  
- Clean missing values  
- Automatic export of cleaned CSV  
- Change report  

## Installation

1. Clone the Portfolio repository:
```bash
git clone https://github.com/Mathéo-Petry/Portfolio.git
```
2. Navigate to the DataCleaner directory:
```bash
cd Portfolio/DataCleaner
```
3. (Optional) Create and activate a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
```
4. Install required packages:
```bash
pip install -r requirements.txt
```

## Usage

```bash
python3 cleaner.py input.csv --dedup --drop-const --missing mean --out cleaned.csv
```

or

```bash
python3 cleaner.py data.tsv --sep '\\t' --drop-const --missing constant --fill '0'
```

## Command-Line Arguments

- `input.csv/tsv`  
    Input CSV or TSV file to be cleaned.

- `--sep SEP`  
    Specify the separator (default: `,`). Example: `--sep '\t'`.

- `--dedup`  
    Remove duplicate rows.

- `--dedup-cols COL1 COL2 ...`  
        Columns to consider when detecting duplicates (optional).

- `--drop-const`  
    Drop columns that contain a single constant value.

- `--missing STRATEGY`  
    How to handle missing values. STRATEGY can be: `drop`, `mean`, `median`, `mode`, `constant`.

- `--fill VALUE`  
    Value to use with `--missing constant`.

- `--missing-cols COL1 COL2 ...`  
    Columns to apply the missing-value strategy to (optional).
