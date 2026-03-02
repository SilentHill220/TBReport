
import os
import shutil
import json
import pandas as pd

# === Configuration ===
SOURCE_EXCEL_PATH = r"H:\SearchFightLeave\config\data\W物品表(新).xlsx"
SOURCE_ICON_PATH = r"H:\SearchFightLeave\client3\Assets\AssetRaw\Modules\AtlasesCommon\IconItem"

TARGET_WIKI_DATA = r"h:\projects\TBData\data\wiki"
TARGET_ASSETS = os.path.join(TARGET_WIKI_DATA, "assets")

# Ensure target directories exist
os.makedirs(TARGET_WIKI_DATA, exist_ok=True)
os.makedirs(TARGET_ASSETS, exist_ok=True)

def import_relics():
    print(f"Reading config from: {SOURCE_EXCEL_PATH}")
    
    # 1. Read the Excel File
    try:
        # Based on typical configurations, Row 2 (index 1) often contains the variable names like 'id', 'loc:name'.
        # We'll try reading with header=1.
        df = pd.read_excel(SOURCE_EXCEL_PATH, header=1, engine='openpyxl')
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return

    # Check if 'id' is in columns; if not, maybe try header=0 or 2
    if 'id' not in df.columns:
        print(f"'id' column not found in header row 1. Columns: {df.columns.tolist()}")
        print("Trying header=0...")
        df = pd.read_excel(SOURCE_EXCEL_PATH, header=0, engine='openpyxl')
        if 'id' not in df.columns:
            print(f"Still not found. Aborting. Available columns: {df.columns.tolist()}")
            return

    # 2. Filter for Relics
    # Condition: BigItemType == 'Remain' AND ItemType == 'remainEquip'
    # Adjust column names for case sensitivity
    
    # Lowercase all columns for safer matching
    df.columns = [str(c).strip() for c in df.columns]
    
    print(f"Columns: {df.columns.tolist()}")
    
    # Identify key columns (handle variations like 'BigItemType' vs 'big_item_type')
    col_big_type = next((c for c in df.columns if c.lower().replace('_', '') == 'bigitemtype'), None)
    col_item_type = next((c for c in df.columns if c.lower().replace('_', '') == 'itemtype'), None)
    col_id = next((c for c in df.columns if c.lower() == 'id'), None)
    col_name = next((c for c in df.columns if 'name' in c.lower() and 'loc' in c.lower()), 'name') # loc:name
    col_desc = next((c for c in df.columns if 'desc' in c.lower() and 'loc' in c.lower()), 'desc') # loc:desc
    col_icon = next((c for c in df.columns if c.lower() == 'icon'), 'icon')
    col_quality = next((c for c in df.columns if 'quality' in c.lower()), 'quality')
    col_cd = next((c for c in df.columns if c.lower() == 'cd'), 'cd')

    if not col_big_type or not col_item_type:
        print("Could not find ItemType columns.")
        return

    count = 0
    updated_count = 0
    
    # Iterate
    for index, row in df.iterrows():
        try:
            b_type = str(row[col_big_type])
            i_type = str(row[col_item_type])
            
            # Filter Logic
            # Note: "Remain" and "remainEquip" are from user screenshot. 
            # Case insensitive check might be safer.
            if b_type.lower() != 'remain' or i_type.lower() != 'remainequip':
                continue

            # Extract Data
            item_id = str(row[col_id]).replace(".0", "") # Remove float decimals if any
            if not item_id or item_id == 'nan':
                continue

            name = str(row[col_name]) if not pd.isna(row[col_name]) else "未知物品"
            desc = str(row[col_desc]) if not pd.isna(row[col_desc]) else ""
            icon_name = str(row[col_icon]) if not pd.isna(row[col_icon]) else ""
            quality = str(row[col_quality]) if not pd.isna(row[col_quality]) else "Common"
            cd = str(row[col_cd]) if not pd.isna(row[col_cd]) else ""

            # Standardize quality name if needed (e.g. 'Uncommon' -> '稀有')
            # Keeping raw for now or mapping? User didn't specify.

            # Construct Wiki Entry
            wiki_id = f"item-{item_id}"
            file_path = os.path.join(TARGET_WIKI_DATA, f"{wiki_id}.json")
            
            # Icon Processing
            icon_url = ""
            if icon_name:
                src_icon = os.path.join(SOURCE_ICON_PATH, f"{icon_name}.png")
                if os.path.exists(src_icon):
                    shutil.copy2(src_icon, os.path.join(TARGET_ASSETS, f"{icon_name}.png"))
                    icon_url = f"/wiki/assets/{icon_name}.png"
                else:
                    # Try finding it in subfolders? Or just log
                    # print(f"Icon missing: {src_icon}")
                    pass

            # Prepare data
            entry_data = {
                "id": wiki_id,
                "type": "item",
                "title": name,
                "subtitle": "遗物",
                "content": desc,
                "icon": icon_url,
                "tags": ["遗物", quality],
                "infobox": {
                    "游戏ID": item_id,
                    "品质": quality,
                    "冷却时间": f"{cd}s" if cd and cd != 'nan' else "无",
                    "类型": "遗物"
                },
                "cover_image": "", 
                "related": []
            }
            
            # Write
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(entry_data, f, ensure_ascii=False, indent=2)
            
            count += 1
            
        except Exception as e:
            print(f"Error processing row {index}: {e}")

    print(f"Import complete. Processed {count} relics.")

if __name__ == "__main__":
    if not os.path.exists(SOURCE_EXCEL_PATH):
        print(f"Source file not found: {SOURCE_EXCEL_PATH}")
    else:
        import_relics()
