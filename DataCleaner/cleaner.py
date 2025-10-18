from __future__ import annotations
import argparse
import csv
import os
import sys
from typing import Optional, Sequence
import pandas as pd

#!/usr/bin/env python3
"""
DataCleaner - simple CSV/TSV/DELIM cleaner

Features:
- Load common delimited files (comma, tab, semicolon, pipe) with automatic delimiter detection
- Remove duplicate rows (optionally by subset of columns)
- Handle missing values: drop rows or fill with mean/median/mode/constant
- Drop constant columns
- Export cleaned file

Usage examples:
$ python cleaner.py in.csv --dedup --missing mean --out cleaned.csv
$ python cleaner.py data.tsv --sep '\\t' --drop-const --missing constant --fill '0'
"""


DELIMITERS = [",", "\t", ";", "|"]

def detect_delimiter(path: str, bytes_to_read: int = 4096) -> Optional[str]:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        sample = f.read(bytes_to_read)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters="".join(DELIMITERS))
        return dialect.delimiter
    except Exception:
        return None


def read_table(path: str, sep: Optional[str] = None) -> pd.DataFrame:
    if sep is None:
        sep = detect_delimiter(path)
    if sep is None:
        # fallback to comma
        sep = ","
    return pd.read_csv(path, sep=sep, engine="python")


def remove_duplicates(df: pd.DataFrame, subset: Optional[Sequence[str]] = None) -> pd.DataFrame:
    return df.drop_duplicates(subset=list(subset) if subset else None, keep="first")


def drop_constant_columns(df: pd.DataFrame) -> pd.DataFrame:
    # consider columns constant if they have <= 1 unique non-NA value
    cols_to_drop = [c for c in df.columns if df[c].nunique(dropna=True) <= 1]
    return df.drop(columns=cols_to_drop)


def fill_missing(
    df: pd.DataFrame,
    strategy: str,
    fill_value: Optional[str] = None,
    subset: Optional[Sequence[str]] = None,
) -> pd.DataFrame:
    target_cols = list(subset) if subset else list(df.columns)
    if strategy == "drop":
        return df.dropna(subset=target_cols)
    if strategy == "constant":
        if fill_value is None:
            raise ValueError("fill_value must be provided for constant strategy")
        return df.fillna(value={c: convert_fill_value(df[c].dtype, fill_value) for c in target_cols})
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
    # try to convert the string fill value to appropriate dtype (int/float/bool), else keep string
    try:
        if pd.api.types.is_integer_dtype(dtype):
            return int(val)
        if pd.api.types.is_float_dtype(dtype):
            return float(val)
        if pd.api.types.is_bool_dtype(dtype):
            low = val.lower()
            if low in ("1", "true", "t", "yes", "y"):
                return True
            if low in ("0", "false", "f", "no", "n"):
                return False
            return bool(val)
    except Exception:
        pass
    return val


def write_table(df: pd.DataFrame, out_path: str) -> None:
    # choose delimiter by extension, default to comma
    _, ext = os.path.splitext(out_path.lower())
    if ext in (".tsv", ".txt"):
        df.to_csv(out_path, sep="\t", index=False)
    else:
        df.to_csv(out_path, index=False)


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="DataCleaner - simple CSV/TSV cleaning utility")
    p.add_argument("input", help="Input delimited file (csv/tsv/other)")
    p.add_argument("--out", "-o", help="Output file path. Defaults to cleaned_<input>", default=None)
    p.add_argument("--sep", help="Force input delimiter (e.g. ',', '\\t', ';', '|')", default=None)
    p.add_argument("--dedup", action="store_true", help="Remove duplicate rows")
    p.add_argument("--dedup-cols", nargs="+", help="Columns to consider for duplicates (optional)", default=None)
    p.add_argument("--drop-const", action="store_true", help="Drop columns with constant values")
    p.add_argument(
        "--missing",
        choices=["drop", "mean", "median", "mode", "constant"],
        default=None,
        help="How to handle missing values",
    )
    p.add_argument("--fill", help="Value to use with --missing constant", default=None)
    p.add_argument("--missing-cols", nargs="+", help="Columns to apply missing handling to (optional)", default=None)
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    inp = args.input
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
            df = fill_missing(df, strategy=args.missing, fill_value=args.fill, subset=args.missing_cols)
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