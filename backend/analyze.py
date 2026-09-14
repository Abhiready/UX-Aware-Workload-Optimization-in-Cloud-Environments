"""
analyze.py — offline analysis over the UX event analytics store (ux_events.db).

Run this after collecting some real usage (or test batches) to produce:
  1. Printed summary stats (frustration rate, signal breakdown, per-user activity)
  2. A saved chart (signal_frequency.png) showing how often each signal fired
     over time, bucketed by minute — the kind of artifact that turns this from
     "a detector" into "an analysis of user behavior."

Usage:
    python analyze.py
"""

import sqlite3
import json
import pandas as pd
import matplotlib.pyplot as plt

DB_PATH = "ux_events.db"


def load_data(db_path: str = DB_PATH) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM batch_analysis", conn)
    conn.close()

    if df.empty:
        return df

    # Parse the JSON signals column into a real list, and derive a datetime
    # column from the batch timestamp for time-based grouping.
    df["signals_list"] = df["signals"].apply(lambda s: json.loads(s) if s else [])
    df["datetime"] = pd.to_datetime(df["batch_ts"], unit="s")
    return df


def print_summary(df: pd.DataFrame) -> None:
    if df.empty:
        print("No data yet — run some test batches or interact with the frontend first.")
        return

    total = len(df)
    frustrated = int(df["frustration_detected"].sum())

    print(f"Total batches analyzed : {total}")
    print(f"Frustration detected   : {frustrated} ({frustrated / total:.1%})")
    print(f"Unique users            : {df['user_id'].nunique()}")
    print()

    # Explode the list of signals per batch into one row per signal, so we can
    # count each signal type independently (a batch can carry >1 signal).
    all_signals = [sig for sigs in df["signals_list"] for sig in sigs]
    if all_signals:
        counts = pd.Series(all_signals).value_counts()
        print("Signal breakdown:")
        for sig, count in counts.items():
            print(f"  {sig:<15} {count}")
    else:
        print("No frustration signals recorded yet.")
    print()

    print("Batches per user:")
    print(df["user_id"].value_counts().to_string())


def plot_signal_frequency(df: pd.DataFrame, out_path: str = "signal_frequency.png") -> None:
    if df.empty or not any(df["signals_list"]):
        print("Skipping chart — no signals to plot yet.")
        return

    # One row per (batch, signal) pair, bucketed by minute.
    rows = []
    for _, row in df.iterrows():
        for sig in row["signals_list"]:
            rows.append({"minute": row["datetime"].floor("min"), "signal": sig})
    long_df = pd.DataFrame(rows)

    pivot = long_df.groupby(["minute", "signal"]).size().unstack(fill_value=0)
    pivot.index = pivot.index.strftime("%H:%M")

    ax = pivot.plot(kind="bar", stacked=True, figsize=(9, 5))
    ax.set_title("Frustration signal frequency over time")
    ax.set_xlabel("Time (minute bucket)")
    ax.set_ylabel("Signal count")
    ax.legend(title="Signal")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    print(f"\nSaved chart to {out_path}")


if __name__ == "__main__":
    df = load_data()
    print_summary(df)
    plot_signal_frequency(df)