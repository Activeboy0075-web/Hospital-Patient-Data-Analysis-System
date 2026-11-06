"""Starter analytics for Hospital Patient Data Analysis System."""
import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def summarize(rows):
    """Return safe baseline descriptive statistics for records from MySQL."""
    df = pd.DataFrame(rows)
    if df.empty:
        return {"row_count": 0, "message": "No records yet. Add sample records to generate analytics."}
    result = {"row_count": int(len(df)), "columns": list(df.columns)}
    numeric = df.select_dtypes(include=["number"])
    result["numeric_summary"] = {}
    for col in numeric.columns:
        values = pd.to_numeric(numeric[col], errors="coerce").dropna()
        if len(values):
            result["numeric_summary"][col] = {
                "mean": round(float(np.mean(values)), 2),
                "median": round(float(np.median(values)), 2),
                "min": float(values.min()), "max": float(values.max())
            }
    # Group any useful categorical column into counts, capped to keep the API response readable.
    result["category_counts"] = {}
    for col in df.select_dtypes(include=["object"]).columns:
        counts = df[col].fillna("Unknown").astype(str).value_counts().head(15)
        result["category_counts"][col] = {str(k): int(v) for k, v in counts.items()}
    return result

def create_chart(rows, output_path):
    """Create a generic numeric column chart; returns None when no chartable data exists."""
    df = pd.DataFrame(rows)
    if df.empty:
        return None
    numeric = df.select_dtypes(include=["number"]).drop(columns=["visit_id"], errors="ignore")
    if numeric.empty:
        return None
    col = numeric.columns[0]
    values = pd.to_numeric(numeric[col], errors="coerce").dropna().head(20)
    if values.empty:
        return None
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.figure(figsize=(9, 4.5))
    plt.bar([str(i + 1) for i in range(len(values))], values.values)
    plt.title(f"Hospital Patient Data Analysis System: sample {col} values")
    plt.xlabel("Record (first 20)")
    plt.ylabel(str(col))
    plt.tight_layout()
    plt.savefig(output_path, dpi=140)
    plt.close()
    return output_path
