import pandas as pd

def clean_excel_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(how='all', axis=0)
    df = df.dropna(how='all', axis=1)
    
    if df.empty: return df
    
    best_row_idx = -1
    threshold = max(2, len(df.columns) * 0.5)
    
    for idx, row in df.head(15).iterrows():
        valid_cells = row.notna().sum()
        if valid_cells >= threshold:
            best_row_idx = idx
            break
            
    if best_row_idx != -1:
        new_header = df.loc[best_row_idx].fillna("")
        
        # In Pandas, multi-level headers might leave blanks.
        # We replace blanks with "Unnamed".
        clean_header = []
        for i, val in enumerate(new_header):
            s = str(val).strip()
            if s == "":
                # sometimes the above header has the text, so let's check
                pass
            clean_header.append(s if s else f"字段_{i}")
            
        df.columns = clean_header
        df = df.loc[best_row_idx + 1:]
        df = df.dropna(how='all', axis=0)
        df.reset_index(drop=True, inplace=True)
        
    return df

df = pd.read_excel('/Users/zewei/Documents/2024-2044/6-Chris/hr-report/人力成本-测试(1).xlsx')
clean_df = clean_excel_df(df)
print("Columns:", clean_df.columns.tolist())
print(clean_df.head(3).to_csv(index=False))

