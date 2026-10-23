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
        candidate_lines = sample_lines
    else:
        # Pre-filter candidate lines
        candidate_lines = [sample_lines[i].strip() for i in data_line_indices]

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

    # Step 5: Detect Skiprows and Header
    # Examine first few candidate lines
    skiprows = 0
    has_header = False
    header_row = None

    if candidate_lines:
        # Find index in sample_lines of first data candidate
        first_candidate_idx = data_line_indices[0] if data_line_indices else 0
        skiprows = first_candidate_idx

        # Check if first candidate row is header (strings) and next rows are numbers
        def tokenize(line_str, delim):
            if delim == r"\s+":
                return re.split(r"\s+", line_str.strip())
            return line_str.split(delim)

        tokens_row0 = tokenize(candidate_lines[0], best_delim)
        numeric_count_row0 = sum(is_numeric_token(t, detected_decimal) for t in tokens_row0)
        
        if len(candidate_lines) > 1:
            tokens_row1 = tokenize(candidate_lines[1], best_delim)
            numeric_count_row1 = sum(is_numeric_token(t, detected_decimal) for t in tokens_row1)
        else:
            numeric_count_row1 = 0

        total_tokens0 = max(1, len(tokens_row0))
        total_tokens1 = max(1, len(tokens_row1)) if len(candidate_lines) > 1 else 1

        # If row 0 is mostly strings (< 50% numbers) but row 1 is mostly numbers (> 70% numbers)
        if (numeric_count_row0 / total_tokens0 < 0.5) and (numeric_count_row1 / total_tokens1 >= 0.6):
            has_header = True
            header_row = skiprows
        elif (numeric_count_row0 / total_tokens0 >= 0.6):
            # Row 0 itself is already numeric -> check if the line immediately before it (in comments) was a header!
            if first_candidate_idx > 0 and detected_comment:
                prev_line = sample_lines[first_candidate_idx - 1].strip()
                if prev_line.startswith(detected_comment):
                    # Strip comment char and check tokens
                    stripped_prev = prev_line.lstrip(detected_comment).strip()
                    prev_tokens = tokenize(stripped_prev, best_delim)
                    prev_num_c = sum(is_numeric_token(t, detected_decimal) for t in prev_tokens)
                    if len(prev_tokens) == len(tokens_row0) and (prev_num_c / len(prev_tokens) < 0.5):
                        # The line before is a header commented out!
                        has_header = True
                        header_row = first_candidate_idx - 1
                        skiprows = first_candidate_idx - 1
                        # Do not treat '#' as comment character in pandas so pandas can read the header row!
                        detected_comment = None
            if not has_header:
                has_header = False
                header_row = None
        else:
            # Check if line 0 might be a title / preamble string
            # Find the first row that is predominantly numeric
            found_numeric_idx = -1
            for idx, line in enumerate(candidate_lines):
                tokens = tokenize(line, best_delim)
                num_c = sum(is_numeric_token(t, detected_decimal) for t in tokens)
                if len(tokens) > 1 and (num_c / len(tokens)) >= 0.7:
                    found_numeric_idx = idx
                    break
            
            if found_numeric_idx > 0:
                # The row before the first numeric row could be the header!
                potential_hdr = candidate_lines[found_numeric_idx - 1]
                hdr_tokens = tokenize(potential_hdr, best_delim)
                if len(hdr_tokens) == len(tokenize(candidate_lines[found_numeric_idx], best_delim)):
                    has_header = True
                    header_row = data_line_indices[found_numeric_idx - 1]
                    skiprows = data_line_indices[found_numeric_idx - 1]
                else:
                    has_header = False
                    skiprows = data_line_indices[found_numeric_idx]
                    header_row = None

    # Step 6: 2D Matrix detection
    # If all values are numeric, no headers, and columns > 5
    is_2d_matrix = False
    if not has_header and best_col_count >= 4 and len(candidate_lines) >= 4:
        # Check if rows are roughly square-ish or wide grid
        is_2d_matrix = False  # Keep false by default for user to toggle, but flag potential

    return {
        "format": "text",
        "encoding": encoding,
        "delimiter": best_delim,
        "skiprows": skiprows,
        "has_header": has_header,
        "header_row": header_row,
        "comment": detected_comment,
        "decimal": detected_decimal,
        "is_2d_matrix": is_2d_matrix,
        "sample_lines": sample_lines
    }


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
                return df, None, ""
            elif arr.ndim == 2:
                df = pd.DataFrame(arr)
                df.columns = [f"Col {i}" for i in range(df.shape[1])]
                return df, arr, ""
            else:
                return None, None, f"Unsupported NumPy array dimensions: {arr.ndim}D"
        except Exception as e:
            return None, None, f"Failed to load NumPy file: {e}"

    # 2. Excel format
    if ext in [".xlsx", ".xls"]:
        try:
            skiprows = params.get("skiprows", 0)
            has_header = params.get("has_header", True)
            header = 0 if has_header else None
            df = pd.read_excel(filepath, skiprows=skiprows, header=header, nrows=max_rows)
            if not has_header:
                df.columns = [f"Col {i}" for i in range(df.shape[1])]
            return df, None, ""
        except Exception as e:
            return None, None, f"Failed to load Excel file: {e}"

    # 3. Text/CSV/TSV/DAT format
    try:
        delimiter = params.get("delimiter", r"\s+")
        skiprows = params.get("skiprows", 0)
        has_header = params.get("has_header", False)
        header_row = 0 if has_header else None
        comment = params.get("comment", None)
        decimal = params.get("decimal", ".")
        encoding = params.get("encoding", "utf-8")
        is_2d_matrix = params.get("is_2d_matrix", False)

        # If delimiter is regex \s+, engine must be 'python'
        engine = "python" if delimiter in [r"\s+", "whitespace", None] or len(delimiter) > 1 else "c"
        sep = r"\s+" if delimiter in [r"\s+", "whitespace"] else delimiter

        # When skipping rows with comment, let pandas handle comment or skiprows
        df = pd.read_csv(
            filepath,
            sep=sep,
            skiprows=skiprows,
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

        return df, matrix, ""
    except Exception as e:
        return None, None, f"Parsing error: {str(e)}"


def evaluate_column_expression(df: pd.DataFrame, new_col_name: str, expression: str) -> Tuple[Optional[pd.DataFrame], str]:
    """
    Safely calculates a new column based on existing columns and numpy functions.
    Includes dedB (reverting dB), dB, gradient, and standard math operations.
    e.g., 'dedB(col)', '10 ** (col / 20)', 'y * 1e3', 'x - x.min()', 'np.log10(np.abs(y))'
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
            "gradient": np.gradient,
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
            safe_name = re.sub(r"\W+", "_", str(col)).strip("_")
            if safe_name:
                safe_dict[safe_name] = df[col]
            safe_dict[str(col)] = df[col]

        res = eval(expression, {"__builtins__": {}}, safe_dict)
        
        new_df = df.copy()
        new_df[new_col_name] = res
        return new_df, ""
    except Exception as e:
        return None, f"Expression calculation error: {str(e)}"
