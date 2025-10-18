#!/usr/bin/env python3

from __future__ import annotations
import argparse
import csv
import os
import sys
from typing import Optional, Sequence
import pandas as pa
import numpy as np

"""
DataCleaner - simple CSV/TSV/DELIM cleaner

Features:
- Load common delimited files (comma, tab, semicolon, pipe) with automatic delimiter detection
- Remove duplicate rows (optionally by subset of columns)
- Handle missing values: drop rows or fill with mean/median/mode/constant
- Drop constant columns
- Export cleaned file
- Create random test CSV/TSV files for quick testing (--pretest)

Options:
    --dedup: Remove duplicate rows
    --dedup-cols COL1 COL2 ...: Columns to consider for duplicates (optional)
    --drop-const: Drop columns with constant values
    --missing STRATEGY: How to handle missing values: "drop", "mean", "median", "mode", "constant"
    --fill VALUE: Value to use with --missing constant
    --missing-cols COL1 COL2 ...: Columns to apply missing handling to (optional)
    --pretest [PATH]: Create sample test_input.csv and test_input.tsv. If PATH is provided and is a directory the files are written into that directory (created if needed). If PATH is a filename ending with .csv/.tsv/.txt, it will be used (and the counterpart file created). If omitted the files are created in the current working directory.

Usage examples:
$ python3 cleaner.py input.csv --dedup --drop-const --missing mean --out cleaned.csv
$ python3 cleaner.py data.tsv --sep '\\t' --drop-const --missing constant --fill '0'
$ python3 cleaner.py --pretest                 # create test_input.csv/test_input.tsv in cwd
$ python3 cleaner.py --pretest /tmp/testdir    # create files in /tmp/testdir
$ python3 cleaner.py --pretest sample.csv      # create sample.csv and sample.tsv in cwd
"""


DELIMITERS = [",", "\t", ";", "|"]


def detect_delimiter(path: str, bytes_to_read: int = 4096) -> Optional[str]:
    """Detect the delimiter in the CSV/TSV file.

    Args:
        path (str): Path to the document
        bytes_to_read (int, optional): Number of bytes to read for delimiter detection. Defaults to 4096.

    Returns:
        out (str): The delimiter of the document
    """

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        sample = f.read(bytes_to_read)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters="".join(DELIMITERS))
        return dialect.delimiter
    except Exception:
        return None


def read_table(path: str, sep: Optional[str] = None) -> pa.DataFrame:
    """Read a CSV/TSV file into a DataFrame.

    Args:
        path (str): Path to the document
        sep (Optional[str], optional): Delimiter to use. If None, auto-detects. Defaults to None.

    Returns:
        out (pa.DataFrame): Loaded DataFrame
    """

    if sep is None:
        sep = detect_delimiter(path)
    if sep is None:
        # fallback to comma
        sep = ","
    return pa.read_csv(path, sep=sep, engine="python")


def remove_duplicates(
    df: pa.DataFrame, subset: Optional[Sequence[str]] = None
) -> pa.DataFrame:
    """Remove duplicate rows from the DataFrame.

    Args:
        df (pa.DataFrame): Input DataFrame
        subset (Optional[Sequence[str]], optional): Columns to consider for duplicates. Defaults to None.

    Returns:
        out (pa.DataFrame): DataFrame with duplicates removed
    """

    return df.drop_duplicates(subset=list(subset) if subset else None, keep="first")


def drop_constant_columns(df: pa.DataFrame) -> pa.DataFrame:
    """Drop columns with constant values from the DataFrame.

    Args:
        df (pa.DataFrame): Input DataFrame

    Returns:
        out (pa.DataFrame): DataFrame with constant columns dropped
    """

    # consider columns constant if they have <= 1 unique non-NA value
    cols_to_drop = [c for c in df.columns if df[c].nunique(dropna=True) <= 1]
    return df.drop(columns=cols_to_drop)


def fill_missing(
    df: pa.DataFrame,
    strategy: str,
    fill_value: Optional[str] = None,
    subset: Optional[Sequence[str]] = None,
) -> pa.DataFrame:
    """Handle missing values in the DataFrame.

    Args:
        df (pa.DataFrame): Input DataFrame
        strategy (str): Strategy to handle missing values: "drop", "mean", "median", "mode", "constant"
        fill_value (Optional[str], optional): Value to use with "constant" strategy. Defaults to None.
        subset (Optional[Sequence[str]], optional): Columns to apply the strategy to. Defaults to None.

    Returns:
        out (pa.DataFrame): DataFrame with missing values handled
    """

    target_cols = list(subset) if subset else list(df.columns)
    if strategy == "drop":
        return df.dropna(subset=target_cols)
    if strategy == "constant":
        if fill_value is None:
            raise ValueError("fill_value must be provided for constant strategy")
        return df.fillna(
            value={c: convert_fill_value(df[c].dtype, fill_value) for c in target_cols}
        )
    if strategy in ("mean", "median"):
        agg = df[target_cols].select_dtypes(include=["number"])
        for c in agg.columns:
            if strategy == "mean":
                v = df[c].mean()
            else:
                v = df[c].median()
            df[c] = df[c].fillna(v)
        # Non-numeric columns: leave as-is
        return df
    if strategy == "mode":
        for c in target_cols:
            modes = df[c].mode(dropna=True)
            if not modes.empty:
                df[c] = df[c].fillna(modes.iloc[0])
        return df
    raise ValueError(f"unknown strategy: {strategy}")


def convert_fill_value(dtype, val: str):
    """Try to convert the string fill value to appropriate dtype (int/float/bool), else keep string

    Args:
        dtype (pa.Series.dtype): _dtype of the column
        val (str): _fill value as string

    Returns:
        out: Converted fill value
    """

    try:
        if pa.api.types.is_integer_dtype(dtype):
            return int(val)
        if pa.api.types.is_float_dtype(dtype):
            return float(val)
        if pa.api.types.is_bool_dtype(dtype):
            low = val.lower()
            if low in ("1", "true", "t", "yes", "y"):
                return True
            if low in ("0", "false", "f", "no", "n"):
                return False
            return bool(val)
    except Exception:
        pass
    return val


def write_table(df: pa.DataFrame, out_path: str) -> None:
    """Write the DataFrame to a delimited file.

    Args:
        df (pa.DataFrame): DataFrame to write
        out_path (str): Output file path
    """

    # choose delimiter by extension, default to comma
    _, ext = os.path.splitext(out_path.lower())
    if ext in (".tsv", ".txt"):
        df.to_csv(out_path, sep="\t", index=False)
    else:
        df.to_csv(out_path, index=False)


def pretest(path: Optional[str] = None) -> None:
    """Create a random csv or tsv file for testing purposes.

    Args:
        path (str, optional): Path or directory to save the test files. If omitted or '.', files are created in the current working directory. If a directory is provided it will be created. If a filename with .csv/.tsv/.txt extension is provided, that file will be used and the counterpart file created alongside it.
    """

    n_rows = 100
    n_cols = 10
    data = {}
    for i in range(n_cols):
        col_name = f"col_{i+1}"
        if i % 3 == 0:
            # numeric column with some missing values
            col_data = np.random.randn(n_rows)
            col_data[np.random.choice(n_rows, size=10, replace=False)] = np.nan
        elif i % 3 == 1:
            # categorical column with some missing values
            choices = ["A", "B", "C", "D"]
            # ensure object dtype so None stays as a proper missing value (not the string 'None')
            col_data = np.random.choice(choices, size=n_rows).astype(object)
            col_data[np.random.choice(n_rows, size=10, replace=False)] = None
        else:
            # constant column
            col_data = ["constant_value"] * n_rows
        data[col_name] = col_data
    df = pa.DataFrame(data)

    # determine output locations
    if path is None or path == "" or path == ".":
        out_dir = "."
        os.makedirs(out_dir, exist_ok=True)
        csv_path = os.path.join(out_dir, "test_input.csv")
        tsv_path = os.path.join(out_dir, "test_input.tsv")
    else:
        # if path is an existing directory or ends with path separator, use as directory
        if os.path.isdir(path) or path.endswith(os.path.sep):
            out_dir = path
            os.makedirs(out_dir, exist_ok=True)
            csv_path = os.path.join(out_dir, "test_input.csv")
            tsv_path = os.path.join(out_dir, "test_input.tsv")
        else:
            base, ext = os.path.splitext(path)
            if ext.lower() in (".csv", ".tsv", ".txt"):
                # use provided filename for one of the outputs and create counterpart
                if ext.lower() == ".csv":
                    csv_path = path
                    tsv_path = f"{base}.tsv"
                else:
                    tsv_path = path
                    csv_path = f"{base}.csv"
                # ensure directory for files exists
                os.makedirs(os.path.dirname(os.path.abspath(csv_path)) or ".", exist_ok=True)
            else:
                # treat as directory name
                out_dir = path
                os.makedirs(out_dir, exist_ok=True)
                csv_path = os.path.join(out_dir, "test_input.csv")
                tsv_path = os.path.join(out_dir, "test_input.tsv")

    df.to_csv(csv_path, index=False)
    df.to_csv(tsv_path, sep="\t", index=False)
    print(f"Created {csv_path} and {tsv_path} for testing.")


def parse_args(argv=None):
    """Parse command-line arguments.

    Args:
        argv (list, optional): List of command-line arguments. Defaults to None.

    Returns:
        out: Parsed arguments
    """

    p = argparse.ArgumentParser(
        description="DataCleaner - simple CSV/TSV cleaning utility"
    )
    p.add_argument("input", nargs="?", help="Input delimited file (csv/tsv/other)")
    p.add_argument(
        "--out",
        "-o",
        help="Output file path. Defaults to cleaned_<input>",
        default=None,
    )
    p.add_argument(
        "--sep", help="Force input delimiter (e.g. ',', '\\t', ';', '|')", default=None
    )
    p.add_argument("--dedup", action="store_true", help="Remove duplicate rows")
    p.add_argument(
        "--dedup-cols",
        nargs="+",
        help="Columns to consider for duplicates (optional)",
        default=None,
    )
    p.add_argument(
        "--drop-const", action="store_true", help="Drop columns with constant values"
    )
    p.add_argument(
        "--missing",
        choices=["drop", "mean", "median", "mode", "constant"],
        default=None,
        help="How to handle missing values",
    )
    p.add_argument("--fill", help="Value to use with --missing constant", default=None)
    p.add_argument(
        "--missing-cols",
        nargs="+",
        help="Columns to apply missing handling to (optional)",
        default=None,
    )
    p.add_argument(
        "--pretest",
        nargs="?",
        const=".",
        default=None,
        help="Create test_input.csv and test_input.tsv. Optionally provide a path/directory/filename.",
    )
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    # handle pretest first
    if args.pretest is not None:
        pretest(args.pretest)
        return

    inp = args.input
    if not inp:
        print("Input file not provided.", file=sys.stderr)
        sys.exit(2)

    if not os.path.isfile(inp):
        print(f"Input file not found: {inp}", file=sys.stderr)
        sys.exit(2)

    try:
        df = read_table(inp, sep=args.sep)
    except Exception as e:
        print(f"Failed to read input: {e}", file=sys.stderr)
        sys.exit(3)

    if args.dedup:
        df = remove_duplicates(df, subset=args.dedup_cols)

    if args.drop_const:
        df = drop_constant_columns(df)

    if args.missing:
        try:
            df = fill_missing(
                df,
                strategy=args.missing,
                fill_value=args.fill,
                subset=args.missing_cols,
            )
        except Exception as e:
            print(f"Missing-handling error: {e}", file=sys.stderr)
            sys.exit(4)

    out_path = args.out or f"cleaned_{os.path.basename(inp)}"
    try:
        write_table(df, out_path)
    except Exception as e:
        print(f"Failed to write output: {e}", file=sys.stderr)
        sys.exit(5)

    print(f"Wrote cleaned file: {out_path}")


if __name__ == "__main__":
    main()
