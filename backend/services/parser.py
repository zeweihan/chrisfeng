"""Excel file parser - handles roster, cost, and salary data files."""
import os
import tempfile
import pandas as pd
from typing import Optional


def _decrypt_if_needed(filepath: str, password: Optional[str] = None) -> str:
    """Decrypt Excel file if password provided. Returns path to readable file."""
    if not password:
        return filepath
    try:
        import msoffcrypto
        
        decrypted = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        with open(filepath, "rb") as f:
            office_file = msoffcrypto.OfficeFile(f)
            office_file.load_key(password=password)
            office_file.decrypt(decrypted)
        return decrypted.name
    except ImportError:
        return filepath
    except Exception as e:
        # If decryption fails, try reading directly
        print(f"Decryption failed ({e}), trying direct read...")
        return filepath


def _clean_excel_df(df: pd.DataFrame) -> pd.DataFrame:
    """Intelligently clean multi-level headers and empty rows."""
    df = df.dropna(how='all', axis=0)
    df = df.dropna(how='all', axis=1)
    if df.empty: return df
    
    # Try to find the actual header row (row with >= 50% non-null values)
    best_row_idx = -1
    threshold = max(2, len(df.columns) * 0.5)
    
    for idx, row in df.head(15).iterrows():
        if row.notna().sum() >= threshold:
            best_row_idx = idx
            break
            
    if best_row_idx != -1:
        new_header = df.loc[best_row_idx].fillna("")
        clean_header = []
        for i, val in enumerate(new_header):
            s = str(val).strip()
            clean_header.append(s if s else f"字段_{i}")
            
        df.columns = clean_header
        df = df.loc[best_row_idx + 1:]
        df = df.dropna(how='all', axis=0)
        df.reset_index(drop=True, inplace=True)
        
    return df



def parse_roster(filepath: str, password: Optional[str] = None) -> dict:
    """Parse employee roster Excel file (在职 + 离职 sheets)."""
    readable_path = _decrypt_if_needed(filepath, password)
    
    try:
        df_active = pd.read_excel(readable_path, sheet_name="在职")
    except Exception:
        df_active = pd.read_excel(readable_path, sheet_name=0)
    
    try:
        df_left = pd.read_excel(readable_path, sheet_name="离职")
    except Exception:
        try:
            df_left = pd.read_excel(readable_path, sheet_name=1)
        except Exception:
            df_left = pd.DataFrame()

    # Normalize column names - handle bilingual headers
    def _norm_cols(df):
        cols = {}
        for c in df.columns:
            parts = str(c).split("/")
            cols[c] = parts[0].strip()
        return df.rename(columns=cols)
    
    df_active = _norm_cols(_clean_excel_df(df_active))
    df_left = _norm_cols(_clean_excel_df(df_left))

    summary = {
        "active_count": len(df_active),
        "left_count": len(df_left),
        "active_columns": list(df_active.columns),
        "left_columns": list(df_left.columns) if len(df_left) > 0 else [],
    }

    # Basic stats from active employees
    if "部门" in df_active.columns:
        dept_counts = df_active["部门"].value_counts().head(15).to_dict()
        summary["departments"] = dept_counts
    
    if "性别" in df_active.columns:
        summary["gender_distribution"] = df_active["性别"].value_counts().to_dict()
    
    if "年龄" in df_active.columns:
        ages = pd.to_numeric(df_active["年龄"], errors="coerce")
        summary["avg_age"] = round(float(ages.mean()), 1) if not ages.empty else None
        summary["age_min"] = int(ages.min()) if not ages.empty else None
        summary["age_max"] = int(ages.max()) if not ages.empty else None

    if "学位" in df_active.columns:
        summary["education"] = df_active["学位"].value_counts().to_dict()
    
    if "级别" in df_active.columns:
        summary["levels"] = df_active["级别"].value_counts().to_dict()

    # Cleanup temp file
    if readable_path != filepath and os.path.exists(readable_path):
        os.unlink(readable_path)

    return summary


def parse_cost_data(filepath: str, password: Optional[str] = None) -> dict:
    """Parse cost/budget data Excel file."""
    readable_path = _decrypt_if_needed(filepath, password)
    df = _clean_excel_df(pd.read_excel(readable_path))
    
    summary = {
        "row_count": len(df),
        "columns": list(df.columns),
        "preview": df.head(5).to_dict(orient="records") if len(df) > 0 else [],
    }
    
    if readable_path != filepath and os.path.exists(readable_path):
        os.unlink(readable_path)
    
    return summary


def parse_salary_data(filepath: str, password: Optional[str] = None) -> dict:
    """Parse salary/compensation data Excel file."""
    readable_path = _decrypt_if_needed(filepath, password)
    df = _clean_excel_df(pd.read_excel(readable_path))
    
    summary = {
        "row_count": len(df),
        "columns": list(df.columns),
        "preview": df.head(5).to_dict(orient="records") if len(df) > 0 else [],
    }
    
    if readable_path != filepath and os.path.exists(readable_path):
        os.unlink(readable_path)
    
    return summary


def load_roster_data(filepath: str, password: Optional[str] = None) -> tuple:
    """Load full roster dataframes for analysis, with PII anonymized."""
    from services.anonymizer import anonymize_data
    readable_path = _decrypt_if_needed(filepath, password)
    
    try:
        df_active = pd.read_excel(readable_path, sheet_name="在职")
    except Exception:
        df_active = pd.read_excel(readable_path, sheet_name=0)
    
    try:
        df_left = pd.read_excel(readable_path, sheet_name="离职")
    except Exception:
        try:
            df_left = pd.read_excel(readable_path, sheet_name=1)
        except Exception:
            df_left = pd.DataFrame()

    def _norm_cols(df):
        cols = {}
        for c in df.columns:
            parts = str(c).split("/")
            cols[c] = parts[0].strip()
        return df.rename(columns=cols)
    
    df_active = _norm_cols(_clean_excel_df(df_active))
    df_left = _norm_cols(_clean_excel_df(df_left))
    
    # Anonymize PII
    df_active = anonymize_data(df_active)
    df_left = anonymize_data(df_left)
    
    if readable_path != filepath and os.path.exists(readable_path):
        os.unlink(readable_path)
    
    return df_active, df_left

def df_to_markdown(df: pd.DataFrame, max_rows: int = 5000) -> str:
    """Convert dataframe to a compact markdown-like CSV string for LLMs."""
    if df is None or df.empty:
        return "数据为空"
    # To save tokens, we use CSV format which LLMs understand perfectly 
    # instead of heavy Markdown pipe table formatting.
    df_subset = df.head(max_rows)
    csv_str = df_subset.to_csv(index=False)
    
    res = f"共 {len(df)} 行数据"
    if len(df) > max_rows:
        res += f"（出于上下文限制，截取前 {max_rows} 行）"
    res += f"：\n```csv\n{csv_str}\n```"
    return res


def df_to_smart_summary(df: pd.DataFrame, label: str = "数据", sample_rows: int = 50) -> str:
    """Convert dataframe to statistical summary + sample rows for token-limited models.
    
    This produces far fewer tokens than full CSV while preserving analytical value:
    - Pandas computes exact statistics (LLMs are bad at counting)
    - A sample of raw rows lets the LLM spot micro-patterns
    """
    if df is None or df.empty:
        return f"{label}为空"
    
    # Deduplicate column names to avoid "ambiguous Series" errors
    df = df.copy()
    seen = {}
    new_cols = []
    for c in df.columns:
        c_str = str(c)
        if c_str in seen:
            seen[c_str] += 1
            new_cols.append(f"{c_str}_{seen[c_str]}")
        else:
            seen[c_str] = 0
            new_cols.append(c_str)
    df.columns = new_cols
    
    lines = [f"【{label}】共 {len(df)} 行, {len(df.columns)} 列"]
    lines.append(f"字段列表: {', '.join(df.columns)}")
    lines.append("")
    
    # --- Categorical column aggregations ---
    cat_fields = ["部门", "性别", "学位", "学历", "级别", "职级", "岗位", "职位", 
                   "合同类型", "用工形式", "国籍", "民族", "婚姻状况", "政治面貌",
                   "离职原因", "离职类型", "招聘渠道", "来源渠道", "前公司",
                   "工作地点", "城市", "上级部门", "子部门", "事业部"]
    
    for col in df.columns:
        try:
            col_str = str(col).strip()
            series = df[col]
            if isinstance(series, pd.DataFrame):
                continue  # Skip if still ambiguous
            
            is_known_cat = any(kw in col_str for kw in cat_fields)
            nunique = int(series.nunique())
            
            if is_known_cat or (nunique <= 30 and nunique > 0):
                vc = series.value_counts()
                if len(vc) > 15:
                    top = vc.head(15)
                    rest_count = int(vc.iloc[15:].sum())
                    dist_str = ", ".join([f"{k}: {v}" for k, v in top.items()])
                    dist_str += f", 其他({len(vc)-15}类): {rest_count}"
                else:
                    dist_str = ", ".join([f"{k}: {v}" for k, v in vc.items()])
                lines.append(f"📊 {col_str} 分布: {dist_str}")
        except Exception as e:
            lines.append(f"📊 {col}: (分析跳过: {e})")
    
    lines.append("")
    
    # --- Numeric column statistics ---
    numeric_fields = ["年龄", "工龄", "司龄", "工资", "薪资", "底薪", "基本工资",
                       "总薪酬", "月薪", "年薪", "奖金", "绩效", "补贴", "社保",
                       "公积金", "成本", "费用", "预算", "金额", "人数", "编制"]
    
    for col in df.columns:
        try:
            col_str = str(col).strip()
            is_known_num = any(kw in col_str for kw in numeric_fields)
            
            if is_known_num:
                series = df[col]
                if isinstance(series, pd.DataFrame):
                    continue
                numeric_vals = pd.to_numeric(series, errors="coerce").dropna()
                if len(numeric_vals) > 0:
                    lines.append(
                        f"📈 {col_str}: 平均={numeric_vals.mean():.1f}, "
                        f"中位数={numeric_vals.median():.1f}, "
                        f"最小={numeric_vals.min():.1f}, 最大={numeric_vals.max():.1f}, "
                        f"总和={numeric_vals.sum():.1f}, 有效数={len(numeric_vals)}"
                    )
        except Exception:
            pass
    
    # --- Date column statistics ---
    date_fields = ["入职日期", "离职日期", "入职时间", "离职时间", "生日", "出生日期",
                    "合同开始", "合同结束", "转正日期"]
    
    for col in df.columns:
        try:
            col_str = str(col).strip()
            is_date = any(kw in col_str for kw in date_fields)
            if is_date:
                series = df[col]
                if isinstance(series, pd.DataFrame):
                    continue
                date_vals = pd.to_datetime(series, errors="coerce").dropna()
                if len(date_vals) > 0:
                    lines.append(
                        f"📅 {col_str}: 最早={date_vals.min().strftime('%Y-%m-%d')}, "
                        f"最晚={date_vals.max().strftime('%Y-%m-%d')}, 有效数={len(date_vals)}"
                    )
                    monthly = date_vals.dt.to_period("M").value_counts().sort_index()
                    if len(monthly) <= 24:
                        month_str = ", ".join([f"{p}: {c}" for p, c in monthly.items()])
                        lines.append(f"   按月分布: {month_str}")
        except Exception:
            pass
    
    lines.append("")
    
    # --- Cross-tabulation: department × key dimensions ---
    try:
        if "部门" in df.columns:
            if "性别" in df.columns:
                cross = pd.crosstab(df["部门"], df["性别"])
                lines.append("📋 部门×性别交叉表:")
                lines.append(cross.to_string())
                lines.append("")
            
            edu_col = None
            for c in ["学位", "学历"]:
                if c in df.columns:
                    edu_col = c
                    break
            if edu_col:
                cross = pd.crosstab(df["部门"], df[edu_col])
                lines.append(f"📋 部门×{edu_col}交叉表:")
                lines.append(cross.to_string())
                lines.append("")
    except Exception:
        pass
    
    # --- Sample raw rows ---
    sample_n = min(sample_rows, len(df))
    lines.append(f"--- 原始数据样本（随机抽取 {sample_n} 行，供微观分析参考）---")
    sample_df = df.sample(n=sample_n, random_state=42)
    lines.append(sample_df.to_csv(index=False))
    
    return "\n".join(lines)


