import pandas as pd
import json

file_path = "/Users/hongchen/Downloads/code/wxz/小龙虾的内容库_内容库_表格.xlsx"

try:
    # Read the Excel file
    df = pd.read_excel(file_path, sheet_name=0) # Read the first sheet
    
    # Get column names
    headers = df.columns.tolist()
    
    # Get top 3 rows of data to understand the content
    sample_data = df.head(3).to_dict(orient='records')
    
    result = {
        "headers": headers,
        "sample_rows": sample_data
    }
    
    print(json.dumps(result, ensure_ascii=False, indent=2))
except Exception as e:
    print(f"Error reading Excel: {e}")
