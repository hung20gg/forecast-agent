import json
import random
import re
import os

vn30_tickers = [
    "ACB", "BCM", "BID", "BVH", "CTG",
    "FPT", "GAS", "GVR", "HDB", "HPG",
    "MBB", "MSN", "MWG", "PLX", "POW",
    "SAB", "SHB", "SSB", "SSI", "STB",
    "TCB", "TPB", "VCB", "VHM", "VIB",
    "VIC", "VJC", "VNM", "VPB", "VRE"
]

def filter_jsonl(filepath, target_stock_count=2000):
    with open(filepath, 'r', encoding='utf-8') as f:
        records = [json.loads(line) for line in f]

    non_stock = []
    vn30_stock = []
    other_stock = []

    # Regex to match stock ticker: matches 3-character uppercase alphanumeric strings
    pattern = re.compile(r"(?:công ty|cổ phiếu|ngân hàng)\s+([A-Z0-9]{3})\b")

    for record in records:
        prompt_content = record['prompt'][0]['content']
        match = pattern.search(prompt_content)
        
        question_type = record.get('extra_info', {}).get('question_type', '')
        
        # Explicit non-stock categories
        if any(question_type.startswith(p) for p in ['macro', 'commodity', 'index']):
            non_stock.append(record)
            continue
            
        if match:
            ticker = match.group(1)
            if ticker in vn30_tickers:
                vn30_stock.append(record)
            else:
                other_stock.append(record)
        else:
            # Fallback if no specific mention of the entity
            non_stock.append(record)

    print(f"\nProcessing: {os.path.basename(filepath)}")
    print(f" - Found {len(vn30_stock)} VN30 samples")
    print(f" - Found {len(other_stock)} other stock samples")
    print(f" - Found {len(non_stock)} non-stock samples")

    # Select stock samples
    selected_stock = []
    
    if len(vn30_stock) >= target_stock_count:
        selected_stock = random.sample(vn30_stock, target_stock_count)
    else:
        selected_stock.extend(vn30_stock)
        remaining = target_stock_count - len(vn30_stock)
        
        # Fill the remaining with randomly sampled other stock samples
        if len(other_stock) >= remaining:
            selected_stock.extend(random.sample(other_stock, remaining))
        else:
            selected_stock.extend(other_stock)

    final_records = non_stock + selected_stock
    random.shuffle(final_records)

    output_filepath = filepath.replace('.jsonl', '_filtered.jsonl')

    # Write to a new _filtered.jsonl file
    with open(output_filepath, 'w', encoding='utf-8') as f:
        for r in final_records:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    print(f" -> Wrote {len(final_records)} total records to {os.path.basename(output_filepath)} (Stock: {len(selected_stock)}, Non-stock: {len(non_stock)}).")


if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, 'data')
    
    val_path = os.path.join(data_dir, 'val.jsonl')
    test_path = os.path.join(data_dir, 'test.jsonl')
    
    if os.path.exists(val_path):
        filter_jsonl(val_path, target_stock_count=2000)
    else:
        print(f"Not found: {val_path}")
        
    if os.path.exists(test_path):
        filter_jsonl(test_path, target_stock_count=2000)
    else:
        print(f"Not found: {test_path}")
