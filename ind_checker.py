"""
ind_checker.py — Cross-reference companies against the IND public sponsor register.
The register is downloaded once and cached locally.
"""

import os
import requests
import pandas as pd
from config import IND_REGISTER_PATH, IND_REGISTER_URL


def _download_register():
    """Download the IND Excel register and convert to a simple CSV."""
    print("  Downloading IND sponsor register...")
    headers = {"User-Agent": "Mozilla/5.0 (compatible; job-pipeline/1.0)"}
    try:
        r = requests.get(IND_REGISTER_URL, headers=headers, timeout=30)
        r.raise_for_status()
        xlsx_path = IND_REGISTER_PATH.replace(".csv", ".xlsx")
        os.makedirs(os.path.dirname(IND_REGISTER_PATH), exist_ok=True)
        with open(xlsx_path, "wb") as f:
            f.write(r.content)
        df = pd.read_excel(xlsx_path, header=None)
        # Flatten all cells into a single column of company names
        names = df.values.flatten()
        names = [str(n).strip().lower() for n in names if pd.notna(n) and str(n).strip()]
        pd.Series(names).drop_duplicates().to_csv(IND_REGISTER_PATH, index=False, header=["name"])
        print(f"  IND register saved ({len(names)} entries).")
        return names
    except Exception as e:
        print(f"  Warning: could not download IND register — {e}")
        return []


def load_sponsors() -> set:
    """Return a set of lowercase sponsor company names."""
    if not os.path.exists(IND_REGISTER_PATH):
        names = _download_register()
        return set(names)
    df = pd.read_csv(IND_REGISTER_PATH)
    return set(df["name"].str.lower().str.strip().tolist())


# Load once at import time
_SPONSORS = None

def is_ind_sponsor(company_name: str) -> str:
    """
    Returns 'Yes', 'No', or 'Unknown' for a company name.
    Uses fuzzy substring matching — e.g. 'booking.com bv' matches 'booking'.
    """
    global _SPONSORS
    if _SPONSORS is None:
        _SPONSORS = load_sponsors()
    if not _SPONSORS:
        return "Unknown"
    needle = company_name.lower().strip()
    # Direct match or substring match in either direction
    for sponsor in _SPONSORS:
        if needle in sponsor or sponsor in needle:
            return "Yes"
    return "No"
