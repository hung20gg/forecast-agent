import json
import random
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar
from google.cloud import bigquery
import math
import os
from uuid import uuid4

# BigQuery Setup
KEY_PATH = '../data_collection/keys/big-query.json'
client = bigquery.Client.from_service_account_json(KEY_PATH)


vn30_tickers = [
    "ACB", "BCM", "BID", "BVH", "CTG",
    "FPT", "GAS", "GVR", "HDB", "HPG",
    "MBB", "MSN", "MWG", "PLX", "POW",
    "SAB", "SHB", "SSB", "SSI", "STB",
    "TCB", "TPB", "VCB", "VHM", "VIB",
    "VIC", "VJC", "VNM", "VPB", "VRE"
]

def get_last_day_of_month(year, month):
    _, last_day = calendar.monthrange(year, month)
    return datetime(year, month, last_day)

def _generate_ask_date_and_gap(target_year, target_time, is_quarter):
    """
    Returns time_asked (str), gap (int).
    For quarters: Q1 -> M:3, Q2 -> M:6, Q3 -> M:9, Q4 -> M:12
    For months: Target is Month M
    """
    if is_quarter:
        target_month = target_time * 3
        # e.g Q3 -> end is month 9
        # Random pick gap logic
        r = random.random()
        if r < 0.45:
            gap = 3  # Target end is month M, ask at end of M-3
        elif r < 0.90:
            gap = 2  # Ask at end of M-2
        else:
            gap = 1  # Ask at end of M-1
    else:
        target_month = target_time
        r = random.random()
        if r < 0.5:
            gap = 2
        else:
            gap = 1
            
    # Calculate ask date
    target_end_date = get_last_day_of_month(target_year, target_month)
    ask_date = target_end_date - relativedelta(months=gap)
    ask_date = get_last_day_of_month(ask_date.year, ask_date.month)
    
    return ask_date.strftime("%Y-%m-%d"), gap

def build_market_query(table_name, target_id_col, time_col='time', join_name_col=None, value_col='close'):
    """Helper to build query for stock, index, commodity"""
    q = f"""
    WITH daily_returns AS (
        SELECT 
            {target_id_col},
            {target_id_col} as name_val,
            {time_col} as time,
            EXTRACT(YEAR FROM {time_col}) as year,
            EXTRACT(QUARTER FROM {time_col}) as quarter,
            EXTRACT(MONTH FROM {time_col}) as month,
            {value_col} as close,
            LAG({value_col}) OVER(PARTITION BY {target_id_col} ORDER BY {time_col}) as prev_close
        FROM `neusolution.ktln.{table_name}`
        WHERE {time_col} >= '2023-05-01'
    ),
    daily_stats AS (
        SELECT
            {target_id_col}, name_val, year, quarter, month, time,
            close, prev_close,
            (close - prev_close) / prev_close as daily_return
        FROM daily_returns
        WHERE time >= '2023-06-01'
    ),
    quarterly_agg AS (
        SELECT 
            {target_id_col}, name_val, year, quarter as time_val, 'quarter' as period_type,
            AVG(close) as mean_close,
            STDDEV_SAMP(close) as std_close,
            STDDEV_SAMP(daily_return) as std_daily_return,
            COUNT(time) as duration,
            ARRAY_AGG(close ORDER BY time DESC LIMIT 1)[OFFSET(0)] as q_close,
            ARRAY_AGG(prev_close ORDER BY time ASC LIMIT 1)[OFFSET(0)] as start_close
        FROM daily_stats
        GROUP BY {target_id_col}, name_val, year, quarter
    ),
    monthly_agg AS (
        SELECT 
            {target_id_col}, name_val, year, month as time_val, 'month' as period_type,
            AVG(close) as mean_close,
            STDDEV_SAMP(close) as std_close,
            STDDEV_SAMP(daily_return) as std_daily_return,
            COUNT(time) as duration,
            ARRAY_AGG(close ORDER BY time DESC LIMIT 1)[OFFSET(0)] as q_close,
            ARRAY_AGG(prev_close ORDER BY time ASC LIMIT 1)[OFFSET(0)] as start_close
        FROM daily_stats
        GROUP BY {target_id_col}, name_val, year, month
    )
    SELECT * FROM quarterly_agg 
    UNION ALL 
    SELECT * FROM monthly_agg
    ORDER BY {target_id_col}, year, time_val
    """
    
    return q

def process_market_df(df, type_prefix, name_map_func=None, price_multiplier=1):
    questions = []
    if df.empty:
        print(f"Warning: Empty dataframe returned for {type_prefix}")
        return questions
        
    df['q_close'] = df['q_close'] * price_multiplier
    df['start_close'] = df['start_close'] * price_multiplier
    df['mean_close'] = df['mean_close'] * price_multiplier
    df['std_close'] = df['std_close'] * price_multiplier
        
    df['return_pct'] = ((df['q_close'] - df['start_close']) / df['start_close']) * 100
    
    for _, row in df.iterrows():
        y = int(row['year'])
        t_val = int(row['time_val'])
        period_type = row['period_type']
        raw_name = row['name_val']
        display_name = raw_name if not name_map_func else name_map_func(raw_name)
        
        # Calculate derived fields
        is_quarter = (period_type == 'quarter')
        ask_date, gap = _generate_ask_date_and_gap(y, t_val, is_quarter)
        
        std_daily = row['std_daily_return']
        duration = row['duration']
        std_vol = std_daily * math.sqrt(duration) if pd.notnull(std_daily) else 0
        
        period_str = f"quý {t_val}" if is_quarter else f"tháng {t_val}"
        
        # Q1: Return
        ret = round(row['return_pct'], 2)
        q_text_ret = f"Tỷ suất sinh lời của {display_name} trong {period_str} năm {y} là bao nhiêu %?"
        questions.append({
            "year": y, "quarter": t_val if is_quarter else None, "time_val": t_val, "is_quarter": is_quarter,
            "question_raw": q_text_ret, "answer_raw": str(ret), "type": f"{type_prefix}_return",
            "time_asked": ask_date, "gap": gap, "std": round(std_vol, 4)
        })
        
        # Q2: Mean + Std
        mean_val = round(row['mean_close'], 2) if pd.notnull(row['mean_close']) else 0
        std_val = round(row['std_close'], 2) if pd.notnull(row['std_close']) else 0
        q_text_stat = f"Giá trị trung bình và độ lệch chuẩn của {display_name} trong {period_str} năm {y} là bao nhiêu?"
        ans_stat = f"Trung bình: {mean_val}, Độ lệch chuẩn: {std_val}"
        questions.append({
            "year": y, "quarter": t_val if is_quarter else None, "time_val": t_val, "is_quarter": is_quarter,
            "question_raw": q_text_stat, "answer_raw": mean_val, "type": f"{type_prefix}_stats",
            "time_asked": ask_date, "gap": gap, "std": round(std_val, 4)
        })
        
    return questions

def generate_stock_data():
    q = build_market_query('stock_daily', 'stock_code')
    df = client.query(q).to_dataframe()
    print("Stock Columns:", df.columns.tolist())
    return process_market_df(df, "stock", lambda n: f"cổ phiếu {n}", price_multiplier=1000)

def generate_index_data():
    q = build_market_query('indices_daily', 'index_name')
    q = q.replace("WHERE time >=", "WHERE index_name IN ('VN30', 'VNINDEX') AND time >=")
    df = client.query(q).to_dataframe()
    return process_market_df(df, "index", lambda n: f"chỉ số {n}")

def generate_commodity_data():
    q = build_market_query('commodities_daily', 'indicator_name', value_col='value')
    q = q.replace("WHERE time >=", "WHERE indicator_name IN ('Gold', 'Silver', 'Brent Crude Oil', 'Crude Oil WTI', 'Natural Gas', 'Gasoline') AND time >=")
    df = client.query(q).to_dataframe()
    commodity_vn = {
        'Gold': 'Vàng', 'Silver': 'Bạc', 
        'Brent Crude Oil': 'Dầu Brent', 'Crude Oil WTI': 'Dầu WTI', 
        'Natural Gas': 'Khí tự nhiên', 'Gasoline': 'Xăng'
    }
    return process_market_df(df, "commodity", lambda n: commodity_vn.get(n, n))


def process_other_df(df, type_prefix, extract_fn):
    questions = []
    for _, row in df.iterrows():
        y, q = int(row['year']), int(row['quarter'])
        
        ask_date, gap = _generate_ask_date_and_gap(y, q, True)
        
        q_text, ans = extract_fn(row, y, q)
        if ans == 'N/A': continue
        
        questions.append({
            "year": y, "quarter": q, "time_val": q, "is_quarter": True,
            "question_raw": q_text, "answer_raw": str(ans), "type": type_prefix(row),
            "time_asked": ask_date, "gap": gap, "std": None
        })
    return questions

def generate_financials_data():
    q = """
    SELECT stock_code, year, quarter, category_code, data, segment
    FROM `neusolution.ktln.financial_statement`
    WHERE category_code IN ('IS_020', 'IS_100', 'BS_125', 'BS_300', 'Bank_TM_121', 'Bank_TM_45', 'Bank_TM_61', 'CF_130') AND year >= 2023 AND quarter > 0
    """
    df = client.query(q).to_dataframe()
    names = {'IS_020': 'Doanh thu', 'IS_100': 'Lợi nhuận ròng', 'BS_125': 'Dư nợ cho vay khách hàng', 'BS_300':'Tổng nợ phải trả', 'IS_049': 'Chi phí lãi vay', 'Bank_TM_121': 'Tiền gửi không kỳ hạn', 'Bank_TM_45': 'Cho vay ngành xây dựng', 'Bank_TM_61': 'Cho vay bất động sản và tư vấn', 'CF_130': 'Tiền và các khoản tương đương tiền tại thời điểm cuối kỳ', 'Bank_TM_72': 'Cho vay ngắn hạn', 'Bank_TM_74': 'Cho vay dài hạn'}
    
    industry_vn = {
        'Basic Resources': 'Tài nguyên Cơ bản', 'Financial Services': 'Dịch vụ Tài chính',
        'Utilities (Electricity, Water & Gas)': 'Tiện ích (Điện, Nước & Khí đốt)', 'Banking': 'Ngân hàng',
        'Food and Beverages': 'Thực phẩm và Đồ uống', 'Retail': 'Bán lẻ',
        'Travel and Leisure': 'Du lịch và Giải trí', 'Chemicals': 'Hóa chất',
        'Information Technology': 'Công nghệ Thông tin', 'Oil and Gas': 'Dầu khí',
        'Real Estate': 'Bất động sản'
    }

    def ext(row, y, q):
        st = row['stock_code']
        st_vn = industry_vn.get(st, st) 
        cat = names[row['category_code']]
        val = row['data']
        segment = str(row.get('segment', '')).lower()
        if segment == 'industry':
            q_text = f"{cat} của ngành {st_vn} trong quý {q} năm {y} là bao nhiêu tỷ VND?"
        elif segment == 'bank':
            q_text = f"{cat} của ngân hàng {st} trong quý {q} năm {y} là bao nhiêu tỷ VND?"
        else:
            q_text = f"{cat} của công ty {st} trong quý {q} năm {y} là bao nhiêu tỷ VND?"
        return q_text, val

    return process_other_df(df, lambda r: f"financial_{r['category_code']}", ext)

def generate_bank_ratios_data():
    q = """
    SELECT stock_code, year, quarter, ratio_code, data
    FROM `neusolution.ktln.financial_ratio`
    WHERE ratio_code IN ('NIM', 'BDR') AND year >= 2023 AND quarter > 0
    """
    df = client.query(q).to_dataframe()
    names = {'NIM': 'NIM', 'BDR': 'Tỷ lệ nợ xấu'}
    
    def ext(row, y, q):
        st = row['stock_code']
        cat = names[row['ratio_code']]
        val = round(row['data'], 4) if pd.notnull(row['data']) else 'N/A'
        q_text = f"{cat} của ngân hàng {st} trong quý {q} năm {y} là bao nhiêu?"
        return q_text, val
        
    return process_other_df(df, lambda r: f"bank_ratio_{r['ratio_code']}", ext)

def generate_ratios_data():
    q = """
    SELECT stock_code, year, quarter, ratio_code, data, segment
    FROM `neusolution.ktln.financial_ratio`
    WHERE ratio_code IN ('NIM', 'BDR', 'ROE', 'ROA', 'EBITDA', 'DTTCR', 'QR', 'CashR') AND year >= 2023 AND quarter > 0 AND segment <> 'industry'
    """

    df = client.query(q).to_dataframe()
    names = {'NIM': 'NIM', 
    'BDR': 'Tỷ lệ nợ xấu', 
    'ROE': 'Tỷ suất sinh lời trên vốn chủ sở hữu', 
    'ROA': 'Tỷ suất sinh lời trên tổng tài sản', 
    'EBITDA': 'EBITDA', 
    'DTTCR': 'Nợ trên tổng vốn chủ sở hữu', 
    'QR': 'Khả năng nhanh toán nhanh', 
    'CashR': 'Khả năng thanh toán nhanh bằng tiền mặt',
    'FCF': 'Dòng tiền tự do',
    'DTER': 'Tỷ lệ nợ trên tổng tài sản'
    }
    
    def ext(row, y, q):
        st = row['stock_code']
        cat = names[row['ratio_code']]
        val = round(row['data'], 4) if pd.notnull(row['data']) else 'N/A'
        segment = str(row.get('segment', '')).lower()

        if segment == 'bank':
            q_text = f"{cat} của ngân hàng {st} trong quý {q} năm {y} là bao nhiêu?"

        else:
            q_text = f"{cat} của công ty {st} trong quý {q} năm {y} là bao nhiêu?"

        return q_text, val
        
    return process_other_df(df, lambda r: f"ratio_{r['ratio_code']}", ext)


def generate_macro_data():
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
    
    def ext(row, y, q):
        ind = 'Lạm phát' if 'Inflation' in row['indicator_name'] else 'Thất nghiệp'
        ret = round(row['increase_pct'], 2)
        q_text = f"Mức thay đổi của Tỷ lệ {ind.lower()} trong quý {q} năm {y} là bao nhiêu %?"
        return q_text, ret
        
    return process_other_df(df, lambda r: f"macro_{r['indicator_name'].split('_')[0].lower()}", ext)

def is_train(y, t_val, is_quarter):
    # Ranged Q3 2023 -> Q2 2025
    if not is_quarter: return False # Skip months for basic check, or keep them?
    q = t_val
    if y == 2023 and q >= 3: return True
    if y == 2024: return True
    if y == 2025 and q <= 2: return True
    return False

def is_test(y, t_val, is_quarter):
    if not is_quarter: return False
    return y == 2025 and t_val == 3

def is_train_inclusive(time_asked):
    # Train set: time_asked < 2025-09-30
    return time_asked < '2025-09-30'

def is_val_inclusive(time_asked):
    # Val set: time_asked is exactly 2025-09-30 or 2025-06-30
    return time_asked in ('2025-09-30', '2025-06-30')

def is_test_inclusive(time_asked):
    # Test set: time_asked > 2025-09-30
    return time_asked > '2025-09-30'

def format_huggingface(item, split, idx):
    extra = {
        "split": split,
        "index": idx,
        "time_asked": item["time_asked"],
        "gap": item["gap"],
        "question_type": item["type"],
        "id": str(uuid4())
    }
    if item["std"] is not None:
        extra["std"] = item["std"]

    try: 
        return {
            "data_source": "ktln",
            "prompt": [{"role": "user", "content": item["question_raw"]}],
            "ability": "math",
            "reward_model": {"style": "rule", "ground_truth": {"mean": float(item["answer_raw"]), "std": item.get("std") or 0}},
            "extra_info": extra
        }
    except:
        print(item)

if __name__ == '__main__':
    print("Fetching data from BigQuery...")
    all_data = []
    
    print("Generating stocks...")
    stock_data = generate_stock_data()
    if len(stock_data) > 3000:
        stock_data = random.sample(stock_data, 4000)
    all_data.extend(stock_data)
    print("Generating index...")
    all_data.extend(generate_index_data())
    print("Generating commodity...")
    all_data.extend(generate_commodity_data())
    print("Generating financials...")
    all_data.extend(generate_financials_data())
    print("Generating bank ratios...")
    all_data.extend(generate_ratios_data())
    print("Generating macro...")
    all_data.extend(generate_macro_data())
    
    train_data = [d for d in all_data if is_train_inclusive(d['time_asked'])]
    val_data   = [d for d in all_data if is_val_inclusive(d['time_asked'])]
    test_data  = [d for d in all_data if is_test_inclusive(d['time_asked'])]
    
    print(f"Total valid generated pairs: {len(all_data)}")
    print(f"Train samples: {len(train_data)}")
    print(f"Val samples:   {len(val_data)}")
    print(f"Test samples:  {len(test_data)}")
    
    random.shuffle(train_data)
    random.shuffle(val_data)
    random.shuffle(test_data)

    os.makedirs('data', exist_ok=True)
    
    # Save train dataset
    with open('data/train.jsonl', 'w', encoding='utf-8') as f:
        for idx, d in enumerate(train_data):
            f.write(json.dumps(format_huggingface(d, "train", idx), ensure_ascii=False) + '\n')

    # Save val dataset
    with open('data/val.jsonl', 'w', encoding='utf-8') as f:
        for idx, d in enumerate(val_data):
            f.write(json.dumps(format_huggingface(d, "val", idx), ensure_ascii=False) + '\n')
            
    # Save test dataset
    with open('data/test.jsonl', 'w', encoding='utf-8') as f:
        for idx, d in enumerate(test_data):
            f.write(json.dumps(format_huggingface(d, "test", idx), ensure_ascii=False) + '\n')
            
    print("Finished generating train.jsonl and test.jsonl")    
