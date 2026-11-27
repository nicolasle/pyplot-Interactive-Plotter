"""
Ultra-Smart Data Loader & Parser
Automatically sniffs delimiter, header presence, comment prefix, skiprows,
and decimal format for scientific files (CSV, TSV, TXT, DAT, Excel, NPY, NPZ).
Allows manual override and live test parsing.
"""

import os
import re
import csv
import io
from collections import Counter
from typing import Dict, Any, Tuple, Optional, List
import pandas as pd
import numpy as np


COMMON_DELIMITERS = [
    ("\t", "Tab (\\t)"),
    (r"\s+", "Whitespace / Multi-space"),
    (",", "Comma (,)"),
    (";", "Semicolon (;)"),
    ("|", "Pipe (|)"),
]

COMMENT_PREFIXES = ["#", "%", "//", ";", "!"]


def detect_encoding(filepath: str) -> str:
    """Detect file encoding safely."""
    for enc in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
        try:
            with open(filepath, "r", encoding=enc) as f:
                f.read(2048)
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return "utf-8"


def get_sample_lines(filepath: str, max_lines: int = 50, encoding: str = "utf-8") -> List[str]:
    """Read first N lines of raw text."""
    lines = []
    try:
        with open(filepath, "r", encoding=encoding, errors="replace") as f:
            for _ in range(max_lines):
                line = f.readline()
                if not line:
                    break
                lines.append(line.rstrip("\r\n"))
    except Exception as e:
        lines.append(f"Error reading file preview: {e}")
    return lines


def is_numeric_token(token: str, decimal: str = ".") -> bool:
    """Check if token can be converted to float."""
    token = token.strip()
    if not token:
        return False
    if decimal == ",":
        token = token.replace(",", ".")
    try:
        float(token)
        return True
    except ValueError:
        return False


def sniff_file_parameters(filepath: str) -> Dict[str, Any]:
    r"""
    Intelligently analyzes a file and infers:
    - encoding
    - comment prefix (if any)
    - number of header/metadata lines to skip
    - delimiter (\t, \s+, comma, semicolon)
    - whether a column header exists
    - decimal character (. vs ,)
    - whether it might be a 2D matrix
    """
    ext = os.path.splitext(filepath)[1].lower()
    
    if ext in [".npy", ".npz"]:
        return {
            "format": "numpy",
            "encoding": "binary",
            "delimiter": None,
            "skiprows": 0,
            "has_header": False,
            "header_row": None,
            "comment": None,
            "decimal": ".",
            "is_2d_matrix": True,
            "sample_lines": ["<Binary NumPy file>"]
        }
    
    if ext in [".xlsx", ".xls"]:
        return {
            "format": "excel",
            "encoding": "binary",
            "delimiter": None,
            "skiprows": 0,
            "has_header": True,
            "header_row": 0,
            "comment": None,
            "decimal": ".",
            "is_2d_matrix": False,
            "sample_lines": ["<Excel spreadsheet>"]
        }

    encoding = detect_encoding(filepath)
    sample_lines = get_sample_lines(filepath, max_lines=60, encoding=encoding)
    
    if not sample_lines:
        return {
            "format": "text",
            "encoding": encoding,
            "delimiter": ",",
            "skiprows": 0,
            "has_header": False,
            "header_row": None,
            "comment": None,
            "decimal": ".",
            "is_2d_matrix": False,
            "sample_lines": []
        }

    # Step 1: Detect comment prefix
    detected_comment = None
    comment_counts = {p: 0 for p in COMMENT_PREFIXES}
    for line in sample_lines[:20]:
        stripped = line.strip()
        for p in COMMENT_PREFIXES:
            if stripped.startswith(p):
                comment_counts[p] += 1
    best_comment, count = max(comment_counts.items(), key=lambda x: x[1])
    if count >= 1:
        detected_comment = best_comment

    # Step 2: Separate comment / preamble lines from data lines
    data_line_indices = []
    for i, line in enumerate(sample_lines):
        stripped = line.strip()
        if not stripped:
            continue
        if detected_comment and stripped.startswith(detected_comment):
            continue
        data_line_indices.append(i)

    if not data_line_indices:
        skiprows = 0
        candidate_lines = [line.rstrip("\r\n") for line in sample_lines]
    else:
        # Pre-filter candidate lines (preserve leading/trailing delimiters like tabs)
        candidate_lines = [sample_lines[i].rstrip("\r\n") for i in data_line_indices]

    # Step 3: Check Decimal Mark (European ',' vs Standard '.')
    # Look for patterns like digit,digit vs digit.digit in non-comment lines
    comma_as_decimal_count = 0
    dot_as_decimal_count = 0
    for line in candidate_lines[:20]:
        comma_as_decimal_count += len(re.findall(r"\d+,\d+", line))
        dot_as_decimal_count += len(re.findall(r"\d+\.\d+", line))
    
    detected_decimal = "."
    if comma_as_decimal_count > dot_as_decimal_count and comma_as_decimal_count > 5:
        # Check if comma could be delimiter or decimal
        # If tabs or semicolons separate numbers with commas, it's definitely a decimal comma!
        detected_decimal = ","

    # Step 4: Delimiter detection
    # Test candidates: Tab, Semicolon, Comma (if not decimal), Whitespace
    candidate_delims = ["\t", ";", r"\s+"]
    if detected_decimal != ",":
        candidate_delims.insert(1, ",")

    best_delim = r"\s+"
    min_variance = 9999.0
    best_col_count = 0

    for delim in candidate_delims:
        col_counts = []
        for line in candidate_lines[:30]:
            if delim == r"\s+":
                tokens = re.split(r"\s+", line.strip())
            else:
                tokens = line.split(delim)
            col_counts.append(len(tokens))
        
        if not col_counts:
            continue
        
        mean_cols = np.mean(col_counts)
        var_cols = np.var(col_counts)
        
        if mean_cols > 1 and var_cols < 0.2:  # very consistent columns
            if var_cols < min_variance:
                min_variance = var_cols
                best_delim = delim
                best_col_count = int(round(mean_cols))

    # If no strict match, re-evaluate with whitespace
    if min_variance > 10 and best_col_count <= 1:
        best_delim = r"\s+"

    # Step 5: Detect Skiprows, Header, and Origin-style metadata rows after header
    skiprows = 0
    skip_after_header = 0
    combine_units_row = False
    has_header = False
    header_row = None

    if candidate_lines:
        # Find index in sample_lines of first data candidate
        first_candidate_idx = data_line_indices[0] if data_line_indices else 0
        skiprows = first_candidate_idx

        def tokenize(line_str, delim):
            if delim == r"\s+":
                return re.split(r"\s+", line_str.strip())
            return line_str.split(delim)

        # Find the first candidate row that is predominantly numeric
        first_numeric_idx = -1
        for idx, line in enumerate(candidate_lines):
            tokens = tokenize(line, best_delim)
            non_empty = [t for t in tokens if t.strip() != ""]
            if not non_empty:
                continue
            num_c = sum(is_numeric_token(t, detected_decimal) for t in non_empty)
            threshold = 0.6 if len(tokens) > 1 else 1.0
            if (num_c / len(non_empty)) >= threshold:
                first_numeric_idx = idx
                break

        if first_numeric_idx == 0:
            # Row 0 itself is already numeric -> check if the line immediately before it (in comments) was a header!
            tokens_row0 = tokenize(candidate_lines[0], best_delim)
            if first_candidate_idx > 0 and detected_comment:
                prev_line = sample_lines[first_candidate_idx - 1].strip()
                if prev_line.startswith(detected_comment):
                    stripped_prev = prev_line.lstrip(detected_comment).strip()
                    prev_tokens = tokenize(stripped_prev, best_delim)
                    prev_num_c = sum(is_numeric_token(t, detected_decimal) for t in prev_tokens)
                    if len(prev_tokens) == len(tokens_row0) and (prev_num_c / max(1, len(prev_tokens)) < 0.5):
                        has_header = True
                        header_row = first_candidate_idx - 1
                        skiprows = first_candidate_idx - 1
                        # Do not treat '#' as comment character in pandas so pandas can read the header row!
                        detected_comment = None
            if not has_header:
                has_header = False
                header_row = None
        elif first_numeric_idx > 0:
            # There are 1 or more non-numeric rows before the first numeric data row.
            # This covers standard 1-row headers AND Origin-style multi-row headers (Name / Units / Comments).
            num_data_cols = len(tokenize(candidate_lines[first_numeric_idx], best_delim))
            hdr_cand_idx = None
            for idx in range(first_numeric_idx):
                cand_tokens = tokenize(candidate_lines[idx], best_delim)
                non_empty_count = sum(1 for t in cand_tokens if t.strip() != "")
                if len(cand_tokens) == num_data_cols and non_empty_count > 0:
                    hdr_cand_idx = idx
                    break

            # Fallback: if no exact column-count match, check the row immediately before data
            if hdr_cand_idx is None:
                prev_tokens = tokenize(candidate_lines[first_numeric_idx - 1], best_delim)
                if len(prev_tokens) == num_data_cols:
                    hdr_cand_idx = first_numeric_idx - 1

            if hdr_cand_idx is not None:
                has_header = True
                header_row = data_line_indices[hdr_cand_idx] if data_line_indices else hdr_cand_idx
                skiprows = header_row
                data_start_line = data_line_indices[first_numeric_idx] if data_line_indices else first_numeric_idx
                skip_after_header = max(0, data_start_line - header_row - 1)
                if skip_after_header >= 1 and header_row + 1 < len(sample_lines):
                    unit_tokens = tokenize(sample_lines[header_row + 1].rstrip("\r\n"), best_delim)
                    if len(unit_tokens) == num_data_cols and any(u.strip() for u in unit_tokens):
                        combine_units_row = True
            else:
                has_header = False
                skiprows = data_line_indices[first_numeric_idx] if data_line_indices else first_numeric_idx
                header_row = None

    # Step 6: 2D Matrix detection
    # If all values are numeric, no headers, and columns > 5
    is_2d_matrix = False
    if not has_header and best_col_count >= 4 and len(candidate_lines) >= 4:
        # Check if rows are roughly square-ish or wide grid
        is_2d_matrix = False  # Keep false by default for user to toggle, but flag potential

    # Step 7: Check for wide condition columns (e.g. Dose 3, Dose 3.4, Dose 3.8)
    wide_prefix, is_wide = None, False
    if has_header and candidate_lines:
        hdr_line = sample_lines[header_row] if header_row is not None and header_row < len(sample_lines) else candidate_lines[0]
        tokens = tokenize(hdr_line, best_delim)
        wide_prefix, is_wide = detect_wide_condition_columns(tokens)

    # Delimiter must never be treated as comment character (e.g. leading empty cells ';;')
    if detected_comment and detected_comment == best_delim:
        detected_comment = None

    return {
        "format": "text",
        "encoding": encoding,
        "delimiter": best_delim,
        "skiprows": skiprows,
        "skip_after_header": skip_after_header,
        "combine_units_row": combine_units_row,
        "has_header": has_header,
        "header_row": header_row,
        "comment": detected_comment,
        "decimal": detected_decimal,
        "is_2d_matrix": is_2d_matrix,
        "is_wide_condition": is_wide,
        "wide_prefix": wide_prefix,
        "sample_lines": sample_lines
    }


def transpose_parsed_data(
    df: Optional[pd.DataFrame],
    matrix: Optional[np.ndarray],
    is_2d_matrix: bool = False,
    has_header: bool = False,
    promote_first_row: bool = False
) -> Tuple[Optional[pd.DataFrame], Optional[np.ndarray]]:
    """
    Transposes the parsed DataFrame and/or 2D matrix.
    Handles column names and numeric conversions appropriately.
    """
    if df is None or df.empty:
        return df, matrix

    if is_2d_matrix:
        if matrix is not None:
            new_matrix = matrix.T
            new_df = pd.DataFrame(new_matrix)
            new_df.columns = [f"Col {i}" for i in range(new_df.shape[1])]
            return new_df, new_matrix
        else:
            new_df = df.T.copy()
            new_df.columns = [f"Col {i}" for i in range(new_df.shape[1])]
            new_df = new_df.reset_index(drop=True)
            try:
                new_matrix = new_df.select_dtypes(include=[np.number]).to_numpy()
            except Exception:
                new_matrix = None
            return new_df, new_matrix

    # If file was parsed with has_header=True and has > 1 column, and user didn't explicitly request row 0 promotion:
    if has_header and len(df.columns) > 1 and not promote_first_row:
        first_col = df.columns[0]
        try:
            df_t = df.set_index(first_col).T.reset_index()
            df_t.columns.name = None
            df_t = df_t.rename(columns={"index": str(first_col)})
            for c in df_t.columns:
                try:
                    df_t[c] = pd.to_numeric(df_t[c])
                except (ValueError, TypeError):
                    pass
            return df_t, None
        except Exception:
            pass

    # Generic 1D table transpose
    df_t = df.T.copy()
    if promote_first_row and len(df_t) > 1:
        raw_headers = [str(c).strip() for c in df_t.iloc[0]]
        seen = {}
        unique_headers = []
        for h in raw_headers:
            base = h if h else "Col"
            if base in seen:
                seen[base] += 1
                unique_headers.append(f"{base}_{seen[base]}")
            else:
                seen[base] = 0
                unique_headers.append(base)
        df_t = df_t.iloc[1:].copy()
        df_t.columns = unique_headers
    else:
        df_t.columns = [f"Col {i}" if isinstance(c, (int, np.integer)) else str(c) for i, c in enumerate(df_t.columns)]

    df_t = df_t.reset_index(drop=True)
    for col in df_t.columns:
        try:
            df_t[col] = pd.to_numeric(df_t[col])
        except (ValueError, TypeError):
            pass

    return df_t, None


def detect_wide_condition_columns(cols: List[str]) -> Tuple[Optional[str], bool]:
    """
    Detects if column headers represent multi-condition repetitions
    (e.g., 'Dose 3', 'Dose 3.4', 'Dose 3.8', or '10', '20', '30').
    Returns (suggested_condition_name, is_detected).
    """
    if not cols or len(cols) < 2:
        return None, False
    prefixes = []
    numbers = []
    for c in cols:
        s = str(c).strip()
        m = re.match(r"^(.*?)\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)\s*(.*?)$", s)
        if m and m.group(2):
            p = m.group(1).strip()
            prefixes.append(p)
            numbers.append(float(m.group(2)))
    if len(numbers) >= max(2, int(len(cols) * 0.6)):
        most_common_p = Counter(prefixes).most_common(1)[0][0] if prefixes else ""
        return (most_common_p or "Condition"), True
    return None, False


def melt_wide_dataframe(
    df: pd.DataFrame,
    var_name: str = "Condition",
    value_name: str = "Value",
    columns_to_melt: Optional[List[str]] = None,
    extract_numeric: bool = True
) -> pd.DataFrame:
    """
    Reshapes a wide table with repeated measurements per condition into long (X, Y) format.
    Extracts numeric values from column names if extract_numeric=True (e.g. 'Dose 3.4' -> 3.4).
    """
    if df is None or df.empty:
        return df

    cols = columns_to_melt if columns_to_melt is not None else list(df.columns)
    df_long = df[cols].melt(var_name=f"{var_name}_label", value_name=value_name).dropna(subset=[value_name])

    if extract_numeric:
        extracted = df_long[f"{var_name}_label"].astype(str).str.extract(
            r"([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)"
        )[0]
        try:
            df_long[var_name] = pd.to_numeric(extracted)
        except Exception:
            df_long[var_name] = extracted
    else:
        df_long[var_name] = df_long[f"{var_name}_label"]
        try:
            df_long[var_name] = pd.to_numeric(df_long[var_name])
        except Exception:
            pass

    try:
        df_long[value_name] = pd.to_numeric(df_long[value_name])
    except Exception:
        pass

    ordered_cols = [var_name, value_name]
    label_col = f"{var_name}_label"
    if label_col in df_long.columns and label_col not in ordered_cols:
        ordered_cols.append(label_col)

    df_res = df_long[ordered_cols].copy()
    if pd.api.types.is_numeric_dtype(df_res[var_name]):
        df_res = df_res.sort_values(by=[var_name]).reset_index(drop=True)
    else:
        df_res = df_res.reset_index(drop=True)

    return df_res


def compute_group_statistics(
    df: pd.DataFrame,
    group_col: str,
    val_col: str
) -> pd.DataFrame:
    """
    Computes summary statistics (mean, std, sem, count, min, max) grouped by group_col.
    """
    if df is None or df.empty or group_col not in df.columns or val_col not in df.columns:
        return pd.DataFrame()

    stats = df.groupby(group_col)[val_col].agg(["mean", "std", "sem", "count", "min", "max"]).reset_index()
    stats.columns = [group_col, f"{val_col}_mean", f"{val_col}_std", f"{val_col}_sem", "count", f"{val_col}_min", f"{val_col}_max"]
    stats[f"{val_col}_std"] = stats[f"{val_col}_std"].fillna(0.0)
    stats[f"{val_col}_sem"] = stats[f"{val_col}_sem"].fillna(0.0)
    return stats


def parse_file(filepath: str, params: Dict[str, Any], max_rows: Optional[int] = None) -> Tuple[Optional[pd.DataFrame], Optional[np.ndarray], str]:
    """
    Parses the file using given parameters.
    Returns (DataFrame, Matrix, ErrorMessage).
    """
    ext = os.path.splitext(filepath)[1].lower()
    
    # 1. Binary NumPy format
    if ext in [".npy", ".npz"]:
        try:
            if ext == ".npy":
                arr = np.load(filepath)
            else:
                data = np.load(filepath)
                # pick first array
                key = list(data.keys())[0]
                arr = data[key]
            
            if arr.ndim == 1:
                df = pd.DataFrame({"Data": arr})
                if params.get("transpose", False):
                    df, _ = transpose_parsed_data(df, None, is_2d_matrix=False, has_header=False)
                return df, None, ""
            elif arr.ndim == 2:
                df = pd.DataFrame(arr)
                df.columns = [f"Col {i}" for i in range(df.shape[1])]
                if params.get("transpose", False):
                    df, arr = transpose_parsed_data(df, arr, is_2d_matrix=True, has_header=False)
                return df, arr, ""
            else:
                return None, None, f"Unsupported NumPy array dimensions: {arr.ndim}D"
        except Exception as e:
            return None, None, f"Failed to load NumPy file: {e}"

    # 2. Excel format
    if ext in [".xlsx", ".xls"]:
        try:
            skiprows = int(params.get("skiprows", 0) or 0)
            skip_after_header = int(params.get("skip_after_header", 0) or 0)
            has_header = params.get("has_header", True)
            header = 0 if has_header else None
            skiprows_arg = (
                list(range(skiprows)) + list(range(skiprows + 1, skiprows + 1 + skip_after_header))
                if has_header and skip_after_header > 0
                else skiprows
            )
            df = pd.read_excel(filepath, skiprows=skiprows_arg, header=header, nrows=max_rows)
            if not has_header:
                df.columns = [f"Col {i}" for i in range(df.shape[1])]
            if params.get("transpose", False):
                df, _ = transpose_parsed_data(
                    df, None,
                    is_2d_matrix=params.get("is_2d_matrix", False),
                    has_header=has_header,
                    promote_first_row=params.get("transpose_header", False)
                )
            if params.get("melt_wide", False) and df is not None and not df.empty:
                var_name = params.get("melt_var_name", "Condition") or "Condition"
                val_name = params.get("melt_val_name", "Value") or "Value"
                extract_num = params.get("melt_extract_numeric", True)
                df = melt_wide_dataframe(
                    df,
                    var_name=var_name,
                    value_name=val_name,
                    extract_numeric=extract_num
                )
            return df, None, ""
        except Exception as e:
            return None, None, f"Failed to load Excel file: {e}"

    # 3. Text/CSV/TSV/DAT format
    try:
        delimiter = params.get("delimiter", r"\s+")
        skiprows = int(params.get("skiprows", 0) or 0)
        skip_after_header = int(params.get("skip_after_header", 0) or 0)
        has_header = params.get("has_header", False)
        header_row = 0 if has_header else None
        comment = params.get("comment", None)
        decimal = params.get("decimal", ".")
        encoding = params.get("encoding", "utf-8")
        is_2d_matrix = params.get("is_2d_matrix", False)

        # If delimiter is regex \s+, engine must be 'python'
        engine = "python" if delimiter in [r"\s+", "whitespace", None] or len(delimiter) > 1 else "c"
        sep = r"\s+" if delimiter in [r"\s+", "whitespace"] else delimiter

        skiprows_arg = (
            list(range(skiprows)) + list(range(skiprows + 1, skiprows + 1 + skip_after_header))
            if has_header and skip_after_header > 0
            else skiprows
        )

        # When skipping rows with comment, let pandas handle comment or skiprows
        df = pd.read_csv(
            filepath,
            sep=sep,
            skiprows=skiprows_arg,
            header=header_row,
            comment=comment,
            decimal=decimal,
            encoding=encoding,
            nrows=max_rows,
            engine=engine,
            on_bad_lines="skip"
        )

        if not has_header:
            df.columns = [f"Col {i}" for i in range(df.shape[1])]
        else:
            # Clean column names (strip whitespace and unprintable characters)
            cleaned_cols = [str(c).strip() for c in df.columns]
            if len(cleaned_cols) > 1 and cleaned_cols[0] in COMMENT_PREFIXES:
                if df.iloc[:, -1].isna().all():
                    df = df.iloc[:, :-1]
                    cleaned_cols = cleaned_cols[1:]
                else:
                    cleaned_cols = [cleaned_cols[0].lstrip("#%/;! ")] + cleaned_cols[1:]
            elif len(cleaned_cols) > 0:
                for p in COMMENT_PREFIXES:
                    if cleaned_cols[0].startswith(p):
                        cleaned_cols[0] = cleaned_cols[0][len(p):].strip()
            df.columns = cleaned_cols

            if skip_after_header >= 1 and params.get("combine_units_row", False):
                try:
                    with open(filepath, "r", encoding=encoding, errors="replace") as uf:
                        for _ in range(skiprows + 1):
                            uf.readline()
                        unit_line = uf.readline().rstrip("\r\n")
                    if unit_line:
                        unit_tokens = (
                            re.split(r"\s+", unit_line.strip())
                            if sep == r"\s+"
                            else unit_line.split(sep)
                        )
                        new_cols = []
                        for i, col_name in enumerate(df.columns):
                            unit = unit_tokens[i].strip() if i < len(unit_tokens) else ""
                            if unit:
                                new_cols.append(f"{col_name} ({unit})")
                            else:
                                new_cols.append(col_name)
                        df.columns = new_cols
                except Exception:
                    pass

        # Convert numeric columns where possible
        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col])
            except (ValueError, TypeError):
                pass

        matrix = None
        if is_2d_matrix:
            try:
                matrix = df.select_dtypes(include=[np.number]).to_numpy()
            except Exception:
                pass

        if params.get("transpose", False):
            df, matrix = transpose_parsed_data(
                df, matrix,
                is_2d_matrix=is_2d_matrix,
                has_header=has_header,
                promote_first_row=params.get("transpose_header", False)
            )

        if params.get("melt_wide", False) and df is not None and not df.empty:
            var_name = params.get("melt_var_name", "Condition") or "Condition"
            val_name = params.get("melt_val_name", "Value") or "Value"
            extract_num = params.get("melt_extract_numeric", True)
            df = melt_wide_dataframe(
                df,
                var_name=var_name,
                value_name=val_name,
                extract_numeric=extract_num
            )
            matrix = None

        return df, matrix, ""
    except Exception as e:
        return None, None, f"Parsing error: {str(e)}"


def differentiate_columns(y: Any, x: Any = None) -> np.ndarray:
    """
    Computes numerical derivative dy/dx using second-order accurate central differences
    (first-order one-sided differences at boundaries).
    
    If x is provided: returns dy/dx (gradient of y with respect to x).
    Handles non-uniform grid spacing in x natively.
    If x is None: returns dy/dn (gradient with step 1.0).
    Always returns an array of the exact same length as y.
    """
    y_arr = np.asarray(y, dtype=float)
    if y_arr.ndim == 0 or len(y_arr) == 0:
        return np.array([], dtype=float)
    if len(y_arr) == 1:
        return np.zeros_like(y_arr)

    # Interpolate NaNs in y if present so gradient doesn't blow up
    if np.isnan(y_arr).any():
        s = pd.Series(y_arr)
        y_arr = s.interpolate().bfill().ffill().to_numpy()

    if x is not None:
        x_arr = np.asarray(x, dtype=float)
        if len(x_arr) != len(y_arr):
            raise ValueError(f"Length mismatch: y has {len(y_arr)} elements, but x has {len(x_arr)} elements.")
        if np.isnan(x_arr).any():
            s_x = pd.Series(x_arr)
            x_arr = s_x.interpolate().bfill().ffill().to_numpy()
        with np.errstate(divide='ignore', invalid='ignore'):
            res = np.gradient(y_arr, x_arr)
        res = np.where(np.isinf(res), np.nan, res)
        return res
    return np.gradient(y_arr)


def apply_gaussian_filter(data: Any, sigma: float = 1.0, mode: str = "reflect") -> np.ndarray:
    """
    Applies a Gaussian blur filter to 1D (or 2D) data.
    sigma: standard deviation in points/samples (> 0).
    """
    arr = np.asarray(data, dtype=float)
    if arr.size == 0:
        return arr
    sigma = max(0.01, float(sigma))

    work_arr = arr
    if np.isnan(arr).any():
        s = pd.Series(arr.flatten())
        work_arr = s.interpolate().bfill().ffill().to_numpy().reshape(arr.shape)

    try:
        from scipy.ndimage import gaussian_filter1d, gaussian_filter
        if arr.ndim == 1:
            return gaussian_filter1d(work_arr, sigma=sigma, mode=mode)
        else:
            return gaussian_filter(work_arr, sigma=sigma, mode=mode)
    except ImportError:
        if arr.ndim == 1:
            radius = int(np.ceil(3.0 * sigma))
            radius = max(1, radius)
            k_x = np.arange(-radius, radius + 1)
            kernel = np.exp(-0.5 * (k_x / sigma) ** 2)
            kernel /= kernel.sum()
            pad_mode = mode if mode in ["reflect", "edge"] else "reflect"
            padded = np.pad(work_arr, radius, mode=pad_mode)
            conv = np.convolve(padded, kernel, mode="same")
            return conv[radius:-radius]
        return work_arr


def apply_median_filter(data: Any, size: int = 3) -> np.ndarray:
    """
    Applies a median filter to remove impulsive noise and outliers.
    size: kernel/window size (odd integer >= 1).
    """
    arr = np.asarray(data, dtype=float)
    if arr.size == 0:
        return arr
    k_size = int(size)
    if k_size % 2 == 0:
        k_size += 1
    k_size = max(1, k_size)
    if arr.ndim == 1 and k_size > len(arr):
        k_size = len(arr) if len(arr) % 2 == 1 else max(1, len(arr) - 1)

    try:
        from scipy.signal import medfilt
        from scipy.ndimage import median_filter
        if arr.ndim == 1:
            return medfilt(arr, kernel_size=k_size)
        else:
            return median_filter(arr, size=k_size)
    except ImportError:
        if arr.ndim == 1:
            return pd.Series(arr).rolling(window=k_size, center=True, min_periods=1).median().to_numpy()
        return arr


def apply_moving_average(data: Any, window: int = 5) -> np.ndarray:
    """
    Applies a moving average (rolling mean) filter.
    window: number of samples in the moving window (>= 1).
    """
    arr = np.asarray(data, dtype=float)
    if arr.size == 0:
        return arr
    win = max(1, int(window))
    if arr.ndim == 1:
        return pd.Series(arr).rolling(window=win, center=True, min_periods=1).mean().to_numpy()
    return arr


def apply_savgol_filter(data: Any, window_length: int = 7, polyorder: int = 2) -> np.ndarray:
    """
    Applies a Savitzky-Golay polynomial smoothing filter.
    Preserves peak shapes, widths, and heights better than standard moving averages.
    """
    arr = np.asarray(data, dtype=float)
    if arr.size == 0:
        return arr
    win = int(window_length)
    if win % 2 == 0:
        win += 1
    win = max(3, win)
    if arr.ndim == 1 and win > len(arr):
        win = len(arr) if len(arr) % 2 == 1 else max(3, len(arr) - 1)
    poly = min(int(polyorder), win - 1)
    try:
        from scipy.signal import savgol_filter
        if arr.ndim == 1 and len(arr) >= win:
            return savgol_filter(arr, window_length=win, polyorder=poly)
    except ImportError:
        pass
    return apply_moving_average(arr, window=win)


def evaluate_column_expression(df: pd.DataFrame, new_col_name: str, expression: str) -> Tuple[Optional[pd.DataFrame], str]:
    """
    Safely calculates a new column based on existing columns and mathematical/smoothing functions.
    Includes:
    - Differentiation: diff(y, x), derivative(y, x), gradient(y, x)
    - Smoothing filters: gaussian_filter(col, sigma), median_filter(col, size), moving_average(col, window), savgol_filter(col, win, poly)
    - Decibel and de-dB: dedB(col), dedB_power(col), to_dB(col), to_dB_power(col)
    - Standard numpy functions: np.log10, np.exp, np.sqrt, np.sin, np.abs, etc.
    """
    try:
        # Helper functions for dB and de-dB operations
        def dedB(x, mode=20):
            """Reverts decibel to linear scale. Default mode=20 (amplitude/voltage), mode=10 (power)."""
            return 10.0 ** (np.asarray(x, dtype=float) / float(mode))

        def dedB_power(x):
            """Reverts decibel for power/intensity: 10 ** (x / 10)."""
            return 10.0 ** (np.asarray(x, dtype=float) / 10.0)

        def to_dB(x, mode=20):
            """Converts linear to decibel. Default mode=20 (amplitude/voltage)."""
            val = np.asarray(x, dtype=float)
            return float(mode) * np.log10(np.abs(val) + 1e-18)

        def to_dB_power(x):
            """Converts power to decibel: 10 * log10(x)."""
            val = np.asarray(x, dtype=float)
            return 10.0 * np.log10(np.abs(val) + 1e-18)

        # Create safe execution environment
        safe_dict = {
            "np": np,
            "numpy": np,
            "sin": np.sin,
            "cos": np.cos,
            "tan": np.tan,
            "exp": np.exp,
            "log": np.log,
            "log10": np.log10,
            "sqrt": np.sqrt,
            "abs": np.abs,
            "gradient": differentiate_columns,
            "diff": differentiate_columns,
            "derivative": differentiate_columns,
            "differentiate": differentiate_columns,
            "gaussian_filter": apply_gaussian_filter,
            "gaussian_blur": apply_gaussian_filter,
            "median_filter": apply_median_filter,
            "medfilt": apply_median_filter,
            "moving_average": apply_moving_average,
            "moving_avg": apply_moving_average,
            "rolling_mean": apply_moving_average,
            "savgol_filter": apply_savgol_filter,
            "savgol": apply_savgol_filter,
            "dedB": dedB,
            "dedb": dedB,
            "dedB_power": dedB_power,
            "dedb_power": dedB_power,
            "to_dB": to_dB,
            "to_db": to_dB,
            "to_dB_power": to_dB_power,
            "dB": to_dB,
            "db": to_dB,
            "df": df
        }
        # Add columns directly to namespace
        for col in df.columns:
            # Clean identifier
            col_str = str(col)
            safe_name = re.sub(r"\W+", "_", col_str).strip("_")
            if safe_name and safe_name[0].isdigit():
                safe_name = f"c_{safe_name}"
            if safe_name:
                safe_dict[safe_name] = df[col]
            safe_dict[str(col)] = df[col]

        res = eval(expression, {"__builtins__": {}}, safe_dict)
        
        new_df = df.copy()
        new_df[new_col_name] = res
        return new_df, ""
    except Exception as e:
        return None, f"Expression calculation error: {str(e)}"
