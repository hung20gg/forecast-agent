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

if __name__ == "__main__":
    test_stock_value()
    test_indices_value()
    test_indices_available()
    test_company_info() 