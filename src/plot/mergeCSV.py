#!/usr/bin/env python3
import os
import sys
import argparse
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from typing import List, Optional, Tuple

import pandas as pd


def choose_files() -> List[str]:
    root = tk.Tk()
    root.withdraw()
    filepaths = filedialog.askopenfilenames(
        title="Select CSV files to merge",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )
    root.update()
    return list(filepaths)


def choose_save_path(default_name: str = "merged.csv") -> Optional[str]:
    root = tk.Tk()
    root.withdraw()
    savepath = filedialog.asksaveasfilename(
        title="Save merged CSV as",
        defaultextension=".csv",
        initialfile=default_name,
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )
    root.update()
    return savepath if savepath else None


def pick_timestamp_column_interactive(columns: List[str]) -> Optional[str]:
    root = tk.Tk()
    root.withdraw()
    msg = (
        "Enter the name of the timestamp column.\n\n"
        f"Available columns:\n{', '.join(columns)}\n"
    )
    col = simpledialog.askstring("Timestamp column", msg)
    root.update()
    return col


def autodetect_timestamp_column(df: pd.DataFrame) -> Optional[str]:
    if df.empty:
        return None

    candidates = [c for c in df.columns if "time" in c.lower() or "date" in c.lower()]
    # Test all columns and choose the one with the most successful parses
    best_col = None
    best_ok = -1
    for col in (candidates or list(df.columns)):
        try:
            # infer_datetime_format has been deprecated/removed in recent pandas versions
            parsed = pd.to_datetime(df[col], errors="coerce", utc=True)
            ok = parsed.notna().sum()
            if ok > best_ok:
                best_ok = ok
                best_col = col
        except Exception:
            continue
    # Require at least one valid parse
    return best_col if best_ok > 0 else None


def normalize_and_read_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["__source_file"] = os.path.basename(path)
    return df


def build_and_save_merge(filepaths: List[str], out_path: str, ts_col: Optional[str] = None) -> Tuple[pd.DataFrame, str]:
    if not filepaths:
        raise ValueError("No input files provided")

    # Read a sample to detect timestamp column if not provided
    sample = normalize_and_read_csv(filepaths[0])
    if ts_col is None:
        ts_col = autodetect_timestamp_column(sample)

    if ts_col is None or ts_col not in sample.columns:
        raise ValueError("Could not determine a valid timestamp column; specify with --timestamp")

    # Read and concat all, aligning columns by name
    frames = [sample]
    for p in filepaths[1:]:
        frames.append(normalize_and_read_csv(p))
    merged = pd.concat(frames, ignore_index=True, sort=False)

    # Parse and sort by timestamp
    merged["__timestamp"] = pd.to_datetime(
        merged[ts_col],
        errors="coerce",
        utc=True,
    )

    # If there are timezone naive values, pandas will coerce to UTC NaT if unparsable
    if merged["__timestamp"].isna().all():
        raise ValueError(f"Failed to parse timestamps in column '{ts_col}'. Try a different column.")

    merged.sort_values("__timestamp", inplace=True)
    # Optional: move helper columns next to timestamp for convenience
    cols = list(merged.columns)
    cols.remove("__timestamp")
    if "__source_file" in cols:
        cols.remove("__source_file")
        ordered_cols = [ts_col, "__timestamp", "__source_file"] + [c for c in cols if c != ts_col]
    else:
        ordered_cols = [ts_col, "__timestamp"] + [c for c in cols if c != ts_col]
    merged = merged[ordered_cols]

    # Save
    merged.to_csv(out_path, index=False, encoding="utf-8-sig")
    return merged, ts_col


def main():
    parser = argparse.ArgumentParser(description="Merge CSV files by timestamp, optionally using a GUI")
    parser.add_argument("files", nargs="*", help="CSV files to merge (CLI mode)")
    parser.add_argument("-o", "--output", help="Output CSV path (CLI mode)")
    parser.add_argument("-t", "--timestamp", help="Timestamp column name (optional)")
    parser.add_argument("--no-gui", action="store_true", help="Force CLI mode; don't open tkinter dialogs")
    args = parser.parse_args()

    interactive = not args.no_gui and len(args.files) == 0

    if interactive:
        try:
            filepaths = choose_files()
            if not filepaths:
                messagebox.showinfo("Merge CSVs", "No files selected. Aborting.")
                return

            # Read a sample to detect timestamp column
            sample = normalize_and_read_csv(filepaths[0])
            ts_col = autodetect_timestamp_column(sample)

            # If auto failed, ask the user
            if ts_col is None:
                ts_col = pick_timestamp_column_interactive(list(sample.columns))
                if not ts_col or ts_col not in sample.columns:
                    messagebox.showerror("Merge CSVs", "Could not determine a valid timestamp column.")
                    return

            # Ask for save path
            out_path = choose_save_path()
            if not out_path:
                messagebox.showinfo("Merge CSVs", "No output path chosen. Aborting.")
                return

            merged, ts_col = build_and_save_merge(
                filepaths=filepaths,
                out_path=out_path,
                ts_col=ts_col,
            )

            messagebox.showinfo(
                "Merge CSVs",
                f"Merged {len(filepaths)} files.\n"
                f"Rows: {len(merged)}\n"
                f"Timestamp column: {ts_col}"
            )
        except Exception as e:
            # In interactive mode, show a dialog
            messagebox.showerror("Merge CSVs", f"An error occurred:\n{e}")
            raise
    else:
        # CLI mode (headless-friendly)
        if not args.files:
            print("Error: No input files provided. Pass file paths or omit to use GUI.", file=sys.stderr)
            sys.exit(2)
        out_path = args.output or os.path.join(os.getcwd(), "merged.csv")
        try:
            merged, ts_col = build_and_save_merge(
                filepaths=list(args.files),
                out_path=out_path,
                ts_col=args.timestamp,
            )
            print(f"Merged {len(args.files)} files into: {out_path}")
            print(f"Rows: {len(merged)}  Timestamp column: {ts_col}")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    # Speed up large reads a bit and avoid dtype warnings
    pd.options.mode.copy_on_write = True
    main()
