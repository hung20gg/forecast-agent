import sys
sys.path.append("../")
import anyio
from client import Client
import os

from tools.get_stock_value import (
    query_stock_value
)

from tools.get_company_detail import (
    query_company_detail,
    query_similar_companies
)

from tools.get_indices_value import (
    query_indices_available,
    query_indices_value
)

from tools.query_news import (
    query_news
)

from tools.get_financial_statement_data import (
    get_exact_financial_ratio_code
)

# Load environment configuration
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))


credentials_path = os.path.join(current_dir, "..", "..", "keys", "bigquery.json")
env_path = os.path.join(current_dir, "..", "..", ".env")

load_dotenv(env_path)

client = Client(
    bq_credentials_path=credentials_path,
    bq_project_id=os.getenv('GCP_PROJECT_ID'),
    limit_time=os.getenv('LIMIT_TIME')
)



def test_stock_value():
    result = anyio.run(query_stock_value, client, "MBB", "2022-01-01", "2022-12-31", "monthly")
    print(result)

    result = anyio.run(query_stock_value, client, "MBB", "2022-01-01", "2022-01-31", "daily")
    print(result)


def test_stock_overtime_value():
    result = anyio.run(query_stock_value, client, "MBB", "2025-01-01", "2025-12-31", "monthly")
    print(result)


def test_stock_overtime_err():
    result = anyio.run(query_stock_value, client, "MBB", "2025-10-01", "2025-12-31", "monthly")
    print(result)

def test_indices_value():
    result = anyio.run(query_indices_value, client, "VNINDEX", "2022-01-01", "2022-12-31", "monthly")
    print(result)

    result = anyio.run(query_indices_value, client, "VNINDEX", "2022-01-01", "2022-01-31", "daily")
    print(result)

def test_indices_available():
    result = anyio.run(query_indices_available, client)
    print(result)

def test_company_info():
    result = anyio.run(query_company_detail, client, "MBB")
    print(result)

# Querying similar ratio codes and names similar to 'non-performing loan ratio'
# INFO:     172.21.0.1:47000 - "GET /sse HTTP/1.1" 200 OK
# [03/09/26 14:59:36] Error calling tool 'get_exact_financial_ratio_code'

# Querying similar ratio codes and names similar to 'debt to total shareholders' equity ratio'
#  Querying similar ratio codes and names similar to 'Return on Assets'
# [03/09/26 15:00:32] Error calling tool 'get_exact_financial_ratio_code'    

def test_get_exact_financial_ratio_code():
    result = anyio.run(get_exact_financial_ratio_code, client, "non-performing loan ratio")
    print(result)

    result = anyio.run(get_exact_financial_ratio_code, client, "debt to total shareholders' equity ratio")
    print(result)



def test_query_news():
    result = anyio.run(query_news, client, "MBB hợp tác quốc tế", "2025-01-01", "2025-12-31")
    print(result)

if __name__ == "__main__":
    # test_stock_value()
    # test_indices_value()
    # test_indices_available()
    # test_company_info() 
    # test_stock_overtime_err()
    # test_query_news()
    test_get_exact_financial_ratio_code()