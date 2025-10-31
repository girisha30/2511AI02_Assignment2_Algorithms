import pandas as pd
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)

# Faculty mapping (numeric code -> short name). Edit if your mapping differs.
FAC_ID_TO_NAME = {
    "1": "ABM", "2": "AE", "3": "AM", "4": "AR", "5": "CA", "6": "JC", "7": "JM", "8": "MA",
    "9": "RH", "10": "RM", "11": "RM2", "12": "RS", "13": "SK", "14": "SKD", "15": "SKM", "16": "SM",
    "17": "SS", "18": "ST"
}

def _map_fac_value(val):
    if pd.isna(val):
        return ""
    s = str(val).strip()
    if s == "":
        return ""
    if s in FAC_ID_TO_NAME:
        return FAC_ID_TO_NAME[s]
    if s.endswith(".0") and s[:-2] in FAC_ID_TO_NAME:
        return FAC_ID_TO_NAME[s[:-2]]
    return s

def _detect_pref_columns(df: pd.DataFrame) -> Tuple[List[str], str]:
    cols = list(df.columns)
    cgpa_idx = None
    cgpa_col = None
    for i, c in enumerate(cols):
        if str(c).strip().lower() in ("cgpa", "cgpa_score", "gpa", "cgpa (out of 10)"):
            cgpa_idx = i
            cgpa_col = c
            break
    if cgpa_idx is None:
        for i, c in enumerate(cols):
            if "cgpa" in str(c).lower():
                cgpa_idx = i
                cgpa_col = c
                break
    if cgpa_idx is None:
        raise ValueError("CGPA column not found.")
    pref_cols = cols[cgpa_idx + 1 :]
    if not pref_cols:
        raise ValueError("No preference columns found after CGPA.")
    return pref_cols, cgpa_col

def _map_pref_columns_to_names(df: pd.DataFrame) -> pd.DataFrame:
    df2 = df.copy()
    pref_cols, _ = _detect_pref_columns(df2)
    for c in pref_cols:
        df2[c] = df2[c].apply(_map_fac_value)
    return df2

def allocate_sorted_by_cgpa(df: pd.DataFrame) -> pd.DataFrame:
    """Return CGPA-sorted df with AllocatedFaculty (names)."""
    try:
        df_mapped = _map_pref_columns_to_names(df)
        pref_cols, cgpa_col = _detect_pref_columns(df_mapped)
        df2 = df_mapped.copy()
        df2[cgpa_col] = pd.to_numeric(df2[cgpa_col], errors="coerce")
        df_sorted = df2.sort_values(by=cgpa_col, ascending=False).reset_index(drop=True)
        n = len(pref_cols)
        allocated = []
        for i, row in df_sorted.iterrows():
            pref_idx = i % n
            assigned_fac = row[pref_cols[pref_idx]]
            allocated.append(assigned_fac)
        df_sorted["AllocatedFaculty"] = allocated
        return df_sorted
    except Exception:
        logger.exception("allocate_sorted_by_cgpa failed")
        raise

def map_allocations_to_original(original_df: pd.DataFrame, alloc_sorted_df: pd.DataFrame) -> pd.DataFrame:
    """
    Map AllocatedFaculty (names) back to the original dataframe order.
    IMPORTANT: This function returns a DataFrame that contains:
      - only the original columns up to CGPA (inclusive), in the same order,
      - plus exactly one appended column: AllocatedFaculty.
    """
    try:
        # Normalize pref values in original so final file contains names
        original_mapped = _map_pref_columns_to_names(original_df)
        out_full = original_mapped.copy().reset_index(drop=True)

        alloc_col = "AllocatedFaculty"
        if alloc_col not in alloc_sorted_df.columns:
            raise ValueError("alloc_sorted_df must contain 'AllocatedFaculty' column")

        # Try to map by a stable id column if present
        id_col = None
        for cand in ["Roll", "RollNo", "Email", "StudentID", "ID"]:
            if cand in out_full.columns and cand in alloc_sorted_df.columns:
                id_col = cand
                break

        if id_col:
            mapping = alloc_sorted_df.set_index(id_col)[alloc_col].to_dict()
            out_full["AllocatedFaculty"] = out_full[id_col].map(mapping)
        else:
            # fallback: align by positional order only if same length
            if len(out_full) != len(alloc_sorted_df):
                raise ValueError("Cannot map allocations: no ID column and row counts differ.")
            out_full["AllocatedFaculty"] = alloc_sorted_df[alloc_col].reset_index(drop=True)

        # Now restrict to original columns up to CGPA (inclusive)
        # Find CGPA index and keep columns from start to CGPA inclusive
        cols = list(original_df.columns)
        cgpa_idx = None
        for i, c in enumerate(cols):
            if str(c).strip().lower() in ("cgpa", "cgpa_score", "gpa", "cgpa (out of 10)") or "cgpa" in str(c).lower():
                cgpa_idx = i
                break
        if cgpa_idx is None:
            # if somehow not found, fall back to keeping all original columns
            kept_cols = cols[:]
        else:
            kept_cols = cols[: cgpa_idx + 1 ]  # include CGPA column
        # Append AllocatedFaculty as single extra column
        final_cols = kept_cols + ["AllocatedFaculty"]
        # Build final df (ensures same original order)
        final_df = out_full[final_cols]

        return final_df
    except Exception:
        logger.exception("map_allocations_to_original failed")
        raise

def build_fac_preference_count(original_df: pd.DataFrame) -> pd.DataFrame:
    """Return DataFrame: Fac, Count Pref 1..N (faculty names)."""
    try:
        df_mapped = _map_pref_columns_to_names(original_df)
        pref_cols, _ = _detect_pref_columns(df_mapped)
        faculty_set = set()
        for c in pref_cols:
            vals = df_mapped[c].astype(str).fillna("").str.strip()
            faculty_set.update([v for v in vals if v != ""])
        faculty_list = sorted(faculty_set)
        n = len(pref_cols)
        rows = []
        for fac in faculty_list:
            row = {"Fac": str(fac)}
            for j in range(1, n + 1):
                row[f"Count Pref {j}"] = 0
            rows.append(row)
        fac_to_row = {r["Fac"]: r for r in rows}
        for j, c in enumerate(pref_cols, start=1):
            vals = df_mapped[c].astype(str).fillna("").str.strip()
            vc = vals[vals != ""].value_counts()
            for fac, cnt in vc.items():
                fac_str = str(fac).strip()
                if fac_str == "":
                    continue
                if fac_str not in fac_to_row:
                    new_row = {"Fac": fac_str}
                    for k in range(1, n + 1):
                        new_row[f"Count Pref {k}"] = 0
                    fac_to_row[fac_str] = new_row
                    rows.append(new_row)
                fac_to_row[fac_str][f"Count Pref {j}"] = int(cnt)
        df_out = pd.DataFrame(rows)
        if "Fac" in df_out.columns:
            cols = ["Fac"] + [c for c in df_out.columns if c != "Fac"]
            df_out = df_out.loc[:, cols]
        else:
            df_out = df_out.reset_index().rename(columns={"index": "Fac"})
        df_out["Fac"] = df_out["Fac"].astype(str)
        df_out = df_out.reset_index(drop=True)
        return df_out
    except Exception:
        logger.exception("build_fac_preference_count failed")
        raise
