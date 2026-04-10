"""Data anonymization service for PII protection."""
import re
import pandas as pd
import hashlib

class Anonymizer:
    def __init__(self):
        self._name_map = {}
        self._name_counter = 1

    def _get_pseudo_name(self, original_name: str) -> str:
        """Map actual names to '员工_001' style systematically."""
        if pd.isna(original_name) or not str(original_name).strip():
            return "未知"
            
        original_name = str(original_name).strip()
        if original_name in self._name_map:
            return self._name_map[original_name]
            
        self._name_map[original_name] = f"员工_{self._name_counter:03d}"
        self._name_counter += 1
        return self._name_map[original_name]

    def anonymize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Anonymize PII columns in a dataframe."""
        if df is None or df.empty:
            return df
            
        df_safe = df.copy()
        
        # Regex patterns to detect PII column names
        name_pattern = re.compile(r"姓名|员工名|Name", re.IGNORECASE)
        id_pattern = re.compile(r"身份|证号|ID", re.IGNORECASE)
        phone_pattern = re.compile(r"手机|电话|联系方式|Phone|Mobile", re.IGNORECASE)
        address_pattern = re.compile(r"地址|住址|Address", re.IGNORECASE)
        
        for col in df_safe.columns:
            col_str = str(col)
            
            # Anonymize names
            if name_pattern.search(col_str) and "公司" not in col_str:
                df_safe[col] = df_safe[col].apply(self._get_pseudo_name)
            
            # Remove or Replace IDs
            elif id_pattern.search(col_str):
                df_safe[col] = "[隐藏_ID]"
                
            # Remove or Replace Phones
            elif phone_pattern.search(col_str):
                df_safe[col] = "[隐藏_手机]"
                
            # Remove or Replace Addresses
            elif address_pattern.search(col_str) and "地点" not in col_str:
                # 保留如"工作地点", "投保地点" (e.g. 北京、上海), 这是业务分析需要的基础信息
                # 如果是详细的居住地址，则隐藏
                if col_str not in ["工作地点", "投保地点", "Working location", "Place of Insurance"]:
                    df_safe[col] = "[隐藏_地址]"
                    
        return df_safe

def anonymize_data(df: pd.DataFrame) -> pd.DataFrame:
    """Convenience function to anonymize a dataframe."""
    anonymizer = Anonymizer()
    return anonymizer.anonymize_dataframe(df)

