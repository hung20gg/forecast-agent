import json
import random
import pandas as pd
from google.cloud import bigquery

# BigQuery Setup
KEY_PATH = '../data_collection/keys/big-query.json'
client = bigquery.Client.from_service_account_json(KEY_PATH)

def generate_stock_data():
    questions = []
    # % Return of a stock within a quarter
    q = """
    SELECT stock_code, EXTRACT(YEAR FROM time) as year, EXTRACT(QUARTER FROM time) as quarter, 
           LAST_VALUE(close) OVER(PARTITION BY stock_code, EXTRACT(YEAR FROM time), EXTRACT(QUARTER FROM time) ORDER BY time ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as q_close
    FROM `neusolution.ktln.stock_monthly`
    WHERE time >= '2023-06-01'
    """
    df = client.query(q).to_dataframe().drop_duplicates()
    df = df.sort_values(by=['stock_code', 'year', 'quarter'])
    df['prev_close'] = df.groupby('stock_code')['q_close'].shift(1)
    df = df.dropna(subset=['prev_close'])
    df['return_pct'] = ((df['q_close'] - df['prev_close']) / df['prev_close']) * 100
    
    for _, row in df.iterrows():
        y, q = int(row['year']), int(row['quarter'])
        st = row['stock_code']
        ret = round(row['return_pct'], 2)
        q_text = f"Tỷ suất sinh lời của cổ phiếu {st} trong quý {q} năm {y} là bao nhiêu %?"
        questions.append({"year": y, "quarter": q, "question_raw": q_text, "answer_raw": str(ret), "type": "stock_return"})
    return questions

def generate_index_data():
    questions = []
    # % Return of VN30 index within a quarter
    q = """
    SELECT index_name, EXTRACT(YEAR FROM time) as year, EXTRACT(QUARTER FROM time) as quarter, 
           LAST_VALUE(close) OVER(PARTITION BY index_name, EXTRACT(YEAR FROM time), EXTRACT(QUARTER FROM time) ORDER BY time ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as q_close
    FROM `neusolution.ktln.indices_monthly`
    WHERE time >= '2023-06-01' AND index_name = 'VN30'
    """
    df = client.query(q).to_dataframe().drop_duplicates()
    df = df.sort_values(by=['index_name', 'year', 'quarter'])
    df['prev_close'] = df.groupby('index_name')['q_close'].shift(1)
    df = df.dropna(subset=['prev_close'])
    df['return_pct'] = ((df['q_close'] - df['prev_close']) / df['prev_close']) * 100
    
    for _, row in df.iterrows():
        y, q = int(row['year']), int(row['quarter'])
        idx_name = row['index_name']
        ret = round(row['return_pct'], 2)
        q_text = f"Tỷ suất sinh lời của chỉ số {idx_name} trong quý {q} năm {y} là bao nhiêu %?"
        questions.append({"year": y, "quarter": q, "question_raw": q_text, "answer_raw": str(ret), "type": "index_return"})
    return questions

def generate_commodity_data():
    questions = []
    # % Increase of specific Commodities within a quarter
    q = """
    SELECT indicator_name, EXTRACT(YEAR FROM time) as year, EXTRACT(QUARTER FROM time) as quarter,
           LAST_VALUE(value) OVER(PARTITION BY indicator_name, EXTRACT(YEAR FROM time), EXTRACT(QUARTER FROM time) ORDER BY time ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as q_close
    FROM `neusolution.ktln.commodities_monthly`
    WHERE indicator_name IN ('Gold', 'Silver', 'Brent Crude Oil', 'Crude Oil WTI', 'Natural Gas', 'Gasoline') AND time >= '2023-06-01'
    """
    df = client.query(q).to_dataframe().drop_duplicates()
    df = df.sort_values(by=['indicator_name', 'year', 'quarter'])
    df['prev_close'] = df.groupby('indicator_name')['q_close'].shift(1)
    df = df.dropna(subset=['prev_close'])
    df['return_pct'] = ((df['q_close'] - df['prev_close']) / df['prev_close']) * 100
    
    commodity_vn = {
        'Gold': 'Vàng', 'Silver': 'Bạc', 
        'Brent Crude Oil': 'Dầu Brent', 'Crude Oil WTI': 'Dầu WTI', 
        'Natural Gas': 'Khí tự nhiên', 'Gasoline': 'Xăng'
    }
    for _, row in df.iterrows():
        y, q = int(row['year']), int(row['quarter'])
        ind = row['indicator_name']
        ind_vn = commodity_vn.get(ind, ind)
        ret = round(row['return_pct'], 2)
        q_text = f"Tỷ lệ tăng giá của {ind_vn} trong quý {q} năm {y} là bao nhiêu %?"
        questions.append({"year": y, "quarter": q, "question_raw": q_text, "answer_raw": str(ret), "type": "commodity_return"})
    return questions

def generate_financials_data():
    questions = []
    # IS_020 = Net Revenue, IS_100 = Net Income, BS_125 = Loans to customers
    q = """
    SELECT stock_code, year, quarter, category_code, data, segment
    FROM `neusolution.ktln.financial_statement`
    WHERE category_code IN ('IS_020', 'IS_100', 'BS_125') AND year >= 2023 AND quarter > 0
    """
    df = client.query(q).to_dataframe()
    names = {'IS_020': 'Doanh thu', 'IS_100': 'Lợi nhuận ròng', 'BS_125': 'Dư nợ cho vay khách hàng'}
    
    industry_vn = {
        'Basic Resources': 'Tài nguyên Cơ bản',
        'Financial Services': 'Dịch vụ Tài chính',
        'Utilities (Electricity, Water & Gas)': 'Tiện ích (Điện, Nước & Khí đốt)',
        'Banking': 'Ngân hàng',
        'Food and Beverages': 'Thực phẩm và Đồ uống',
        'Retail': 'Bán lẻ',
        'Travel and Leisure': 'Du lịch và Giải trí',
        'Chemicals': 'Hóa chất',
        'Information Technology': 'Công nghệ Thông tin',
        'Oil and Gas': 'Dầu khí',
        'Real Estate': 'Bất động sản'
    }

    for _, row in df.iterrows():
        y, q = int(row['year']), int(row['quarter'])
        st = row['stock_code']
        st_vn = industry_vn.get(st, st) # Fallback to original name if not in dict
        
        cat = names[row['category_code']]
        val = row['data']
        segment = str(row.get('segment', '')).lower()
        
        if segment == 'industry':
            q_text = f"{cat} của ngành {st_vn} trong quý {q} năm {y} là bao nhiêu?"
        elif segment == 'bank':
            q_text = f"{cat} của ngân hàng {st} trong quý {q} năm {y} là bao nhiêu?"
        else:
            q_text = f"{cat} của công ty {st} trong quý {q} năm {y} là bao nhiêu?"
            
        questions.append({"year": y, "quarter": q, "question_raw": q_text, "answer_raw": str(val), "type": f"financial_{row['category_code']}"})
    return questions

def generate_bank_ratios_data():
    questions = []
    q = """
    SELECT stock_code, year, quarter, ratio_code, data
    FROM `neusolution.ktln.financial_ratio`
    WHERE ratio_code IN ('NIM', 'BDR') AND year >= 2023 AND quarter > 0
    """
    df = client.query(q).to_dataframe()
    names = {'NIM': 'NIM', 'BDR': 'Tỷ lệ nợ xấu'}
    
    for _, row in df.iterrows():
        y, q = int(row['year']), int(row['quarter'])
        st = row['stock_code']
        cat = names[row['ratio_code']]
        val = round(row['data'], 4) if pd.notnull(row['data']) else 'N/A'
        if val == 'N/A': continue
        
        q_text = f"{cat} của ngân hàng {st} trong quý {q} năm {y} là bao nhiêu?"
        questions.append({"year": y, "quarter": q, "question_raw": q_text, "answer_raw": str(val), "type": f"bank_ratio_{row['ratio_code']}"})
    return questions

def generate_macro_data():
    questions = []
    q = """
    SELECT indicator_name, EXTRACT(YEAR FROM datetime) as year, EXTRACT(QUARTER FROM datetime) as quarter,
           LAST_VALUE(value) OVER(PARTITION BY indicator_name, EXTRACT(YEAR FROM datetime), EXTRACT(QUARTER FROM datetime) ORDER BY datetime ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as q_close
    FROM `neusolution.ktln.macro`
    WHERE indicator_name IN ('Inflation_%', 'Unemployment_%') AND datetime >= '2023-06-01'
    """
    df = client.query(q).to_dataframe().drop_duplicates()
    df = df.sort_values(by=['indicator_name', 'year', 'quarter'])
    df['prev_close'] = df.groupby('indicator_name')['q_close'].shift(1)
    df = df.dropna(subset=['prev_close'])
    df['increase_pct'] = ((df['q_close'] - df['prev_close']) / df['prev_close']) * 100
    
    for _, row in df.iterrows():
        y, q = int(row['year']), int(row['quarter'])
        ind = 'Lạm phát' if 'Inflation' in row['indicator_name'] else 'Thất nghiệp'
        ret = round(row['increase_pct'], 2)
        q_text = f"Mức thay đổi của Tỷ lệ {ind.lower()} trong quý {q} năm {y} là bao nhiêu %?"
        questions.append({"year": y, "quarter": q, "question_raw": q_text, "answer_raw": str(ret), "type": f"macro_{ind}"})
    return questions

def is_train(y, q):
    if y == 2023 and q >= 3: return True
    if y == 2024: return True
    if y == 2025 and q <= 2: return True
    return False

def is_test(y, q):
    return y == 2025 and q == 3

def format_huggingface(item, split, idx):
    return {
        "data_source": "ktln",
        "prompt": [{"role": "user", "content": item["question_raw"]}],
        "ability": "math",
        "reward_model": {"style": "rule", "ground_truth": item["answer_raw"]},
        "extra_info": {
            "split": split,
            "index": idx,
            "answer": item["answer_raw"],
            "question": item["question_raw"],
        }
    }

if __name__ == '__main__':
    print("Fetching data from BigQuery...")
    all_data = []
    all_data.extend(generate_stock_data())
    all_data.extend(generate_index_data())
    all_data.extend(generate_commodity_data())
    all_data.extend(generate_financials_data())
    all_data.extend(generate_bank_ratios_data())
    all_data.extend(generate_macro_data())
    
    train_data = [d for d in all_data if is_train(d['year'], d['quarter'])]
    test_data = [d for d in all_data if is_test(d['year'], d['quarter'])]
    
    print(f"Total valid generated pairs: {len(all_data)}")
    print(f"Train samples: {len(train_data)}")
    print(f"Test samples: {len(test_data)}")
    
    random.shuffle(train_data)
    random.shuffle(test_data)
    
    # Save train dataset
    with open('train.jsonl', 'w', encoding='utf-8') as f:
        for idx, d in enumerate(train_data):
            f.write(json.dumps(format_huggingface(d, "train", idx), ensure_ascii=False) + '\n')
            
    # Save test dataset
    with open('test.jsonl', 'w', encoding='utf-8') as f:
        for idx, d in enumerate(test_data):
            f.write(json.dumps(format_huggingface(d, "test", idx), ensure_ascii=False) + '\n')
            
    print("Finished generating train.jsonl and test.jsonl")
