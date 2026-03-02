
import os
import shutil
import json
import pandas as pd
import re

# === Configuration ===
SOURCE_EXCEL_PATH = r"H:\SearchFightLeave\config\data\T天赋表.xlsx"
SOURCE_ICON_PATH = r"H:\SearchFightLeave\client3\Assets\AssetRaw\Modules\AtlasesCommon\TalentCard"
TARGET_WIKI_DATA = r"h:\projects\TBData\data\wiki"
TARGET_ASSETS = os.path.join(TARGET_WIKI_DATA, "assets")

# Ensure target directories exist
os.makedirs(TARGET_WIKI_DATA, exist_ok=True)
os.makedirs(TARGET_ASSETS, exist_ok=True)

def parse_pre(pre_str):
    """
    Parses 'talent_pre' string.
    Examples: 
      'talent#308' -> Parent 308
      'talentBreakThrough#0' -> Root (No parent dependency)
    Returns a list of parent IDs (if 'talent#ID').
    """
    if pd.isna(pre_str) or not isinstance(pre_str, str):
        return []
    
    parents = []
    matches = re.findall(r'talent#(\d+)', pre_str)
    parents.extend(matches)
    
    return parents

def import_talents():
    print(f"Reading config from: {SOURCE_EXCEL_PATH}")
    
    try:
        df = pd.read_excel(SOURCE_EXCEL_PATH, header=0, engine='openpyxl')
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return

    # Normalize columns
    df.columns = [str(c).strip() for c in df.columns]
    
    # Find columns
    # Find columns based on Chinese headers
    col_id = 'ID'
    
    # Name column prioritization
    col_name = None
    possible_name_cols = ['天赋名称 (备注用)', '天赋名称', '名字', '名称']
    for candidate in possible_name_cols:
        if candidate in df.columns:
            col_name = candidate
            break
    if not col_name:
        # Fuzzy search
        col_name = next((c for c in df.columns if '名称' in c), None)

    col_desc = '天赋描述' if '天赋描述' in df.columns else '描述'
    col_group = '客户端天赋分组'
    col_pre = '天赋条件'
    col_type = '天赋种 类' if '天赋种 类' in df.columns else '天赋种类' # Handle potential spacing
    col_icon = '天赋图标'
    
    # Fallback search if exact main logic fails
    if col_group not in df.columns:
        col_group = next((c for c in df.columns if '分组' in c), None)

    if not col_id:
        print("CRITICAL: 'id' column not found.")
        return

    count = 0
    for index, row in df.iterrows():
        try:
            # ID
            raw_id = row[col_id]
            if pd.isna(raw_id) or str(raw_id).lower() == 'nan' or str(raw_id).lower() == 'null':
                continue
            item_id = str(raw_id).replace(".0", "")
            
            # Name
            name = "未知天赋"
            if col_name and not pd.isna(row[col_name]):
                name = str(row[col_name])
            
            # Group
            group_id = "0"
            if col_group in df.columns and not pd.isna(row[col_group]):
                group_id = str(row[col_group]).replace(".0", "")
            
            # Pre
            pre_raw = ""
            if col_pre in df.columns and not pd.isna(row[col_pre]):
                pre_raw = str(row[col_pre])
            parent_ids = parse_pre(pre_raw)
            
            # Desc
            desc = ""
            if col_desc and col_desc in df.columns and not pd.isna(row[col_desc]):
                desc = str(row[col_desc])
                
            # Icon
            icon_url = ""
            if col_icon in df.columns and not pd.isna(row[col_icon]):
                icon_name = str(row[col_icon])
                # Try finding icon file
                # Check for png
                src_icon = os.path.join(SOURCE_ICON_PATH, f"{icon_name}.png")
                if not os.path.exists(src_icon):
                    # Try other formats or exact name? User said path is AtlasesCommon/TalentCard
                    pass
                
                if os.path.exists(src_icon):
                    shutil.copy2(src_icon, os.path.join(TARGET_ASSETS, f"{icon_name}.png"))
                    icon_url = f"/wiki/assets/{icon_name}.png"


            # Wiki Entry Construct
            wiki_id = f"talent-{item_id}"
            file_path = os.path.join(TARGET_WIKI_DATA, f"{wiki_id}.json")
            
            entry_data = {
                "id": wiki_id,
                "type": "talent",
                "title": name,
                "subtitle": f"组: {group_id}",
                "content": desc or "暂无描述",
                "icon": icon_url, 
                "tags": ["天赋", f"Group:{group_id}"],
                "infobox": {
                    "游戏ID": item_id,
                    "天赋组": group_id,
                    "前置条件": pre_raw,
                    "类型": str(row[col_type]) if col_type in df.columns else "未知"
                },
                "talent_meta": {
                    "group_id": group_id,
                    "parents": parent_ids,
                    "raw_pre": pre_raw
                },
                "related": [f"talent-{pid}" for pid in parent_ids]
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(entry_data, f, ensure_ascii=False, indent=2)
            
            count += 1
            
        except Exception as e:
            print(f"Error processing row {index}: {e}")

    print(f"Import complete. Imported {count} talents.")

if __name__ == "__main__":
    if not os.path.exists(SOURCE_EXCEL_PATH):
        print(f"Source file not found: {SOURCE_EXCEL_PATH}")
    else:
        import_talents()
