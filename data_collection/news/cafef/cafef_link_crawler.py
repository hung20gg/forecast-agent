from bs4 import BeautifulSoup
from curl_cffi import requests
import re
from google.cloud import bigquery
from datetime import datetime
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
        # "Referer": "https://vietcv.seedoo.vn/",
        # Đừng quên tham số từ Local Storage bạn đã tìm thấy
    }

session = requests.Session()

# Initialize BigQuery client with service account key
KEY_PATH = os.path.join(os.path.dirname(__file__), '../../keys/big-query.json')
bq_client = bigquery.Client.from_service_account_json(KEY_PATH)

# Update these with your project and dataset
PROJECT_ID = 'neusolution'
DATASET_ID = 'raw'
TABLE_ID = 'news'
TABLE_FULL_ID = f'{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}'

channelIDs = [
 (188112, 'Xã hội'),
 (18831, 'Chứng khoán'),
 (18835, 'Bất động sản'),
 (18836, 'Doanh nghiệp'),
 (18834, 'Ngân hàng'),
 (1882020, 'Smart money'),
 (18832, 'Tài chính quốc tế'),
 (18833, 'Vĩ mô'),
 (188127, 'Kinh tế số'),
 (18839, 'Thị trường')
]

def fetch_links(channel_info: tuple[int, str], page_num: int):

    channelID, channelname = channel_info

    url_fetch = f'https://cafef.vn/timelinelist/{channelID}/{page_num}.chn'

    response = session.get(
        url=url_fetch,
        headers=headers
    )
    # Find all links matching the pattern /yyyy/mm/text.htm
    html_content = response.text
    soup = BeautifulSoup(html_content, 'html.parser')

    pattern = r'href="([^"]+\.chn)"'
    links = re.findall(pattern, soup.prettify())

    set_links = set(links)
    return list(set_links)


def create_table_if_not_exists():
    """Create BigQuery table if it doesn't exist"""
    dataset_ref = bigquery.DatasetReference(PROJECT_ID, DATASET_ID)
    
    # Create dataset if it doesn't exist
    try:
        bq_client.get_dataset(dataset_ref)
    except Exception:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "asia-southeast1"
        bq_client.create_dataset(dataset)
        print(f"Created dataset {DATASET_ID}")
    
    # Define table schema
    schema = [
        bigquery.SchemaField("url", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("source", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("channel_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("channel_id", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("updated_at", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("text", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("summarize", "STRING", mode="NULLABLE"),
    ]
    
    # Create table if it doesn't exist
    try:
        table = bq_client.get_table(TABLE_FULL_ID)
        print(f"Table {TABLE_ID} already exists")
    except Exception as e:
        print(f"Table doesn't exist, creating: {e}")
        table = bigquery.Table(TABLE_FULL_ID, schema=schema)
        table = bq_client.create_table(table)
        print(f"Created table {TABLE_ID} with schema")


def save_url_to_bigquery(url: str, channel_name: str, channel_id: int):
    """
    Save crawled URL to BigQuery using MERGE (insert if not exists).
    Initially saves only URL and metadata, text and summarize will be added later.
    """
    now = datetime.now().isoformat()
    
    # Use MERGE to insert only if URL doesn't exist
    merge_query = f"""
    MERGE `{TABLE_FULL_ID}` T
    USING (SELECT 
        @url AS url,
        @source AS source,
        @channel_name AS channel_name,
        @channel_id AS channel_id,
        @created_at AS created_at,
        @updated_at AS updated_at,
        @text AS text,
        @summarize AS summarize
    ) S
    ON T.url = S.url
    WHEN NOT MATCHED THEN
        INSERT (url, source, channel_name, channel_id, created_at, updated_at, text, summarize)
        VALUES (url, source, channel_name, channel_id, created_at, updated_at, text, summarize)
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("url", "STRING", url),
            bigquery.ScalarQueryParameter("source", "STRING", "cafef"),
            bigquery.ScalarQueryParameter("channel_name", "STRING", channel_name),
            bigquery.ScalarQueryParameter("channel_id", "INTEGER", channel_id),
            bigquery.ScalarQueryParameter("created_at", "TIMESTAMP", now),
            bigquery.ScalarQueryParameter("updated_at", "TIMESTAMP", now),
            bigquery.ScalarQueryParameter("text", "STRING", None),
            bigquery.ScalarQueryParameter("summarize", "STRING", None),
        ]
    )
    
    try:
        query_job = bq_client.query(merge_query, job_config=job_config)
        result = query_job.result()
        
        # Check if row was inserted
        if query_job.num_dml_affected_rows > 0:
            print(f"Saved new URL: {url}")
            return True
        else:
            print(f"URL already exists: {url}")
            return False
    except Exception as e:
        print(f"Error saving URL {url}: {e}")
        return False


def crawl_and_save(channel_info: tuple[int, str], page_num: int):
    """Fetch links and save them to BigQuery"""
    channel_id, channel_name = channel_info
    
    print(f"Crawling {channel_name} (ID: {channel_id}), page {page_num}")
    links = fetch_links(channel_info, page_num)
    
    saved_count = 0
    for link in links:
        # Convert relative URLs to absolute if needed
        if not link.startswith('http'):
            link = f'https://cafef.vn{link}'
        
        if save_url_to_bigquery(link, channel_name, channel_id):
            saved_count += 1
    
    print(f"Saved {saved_count} new URLs out of {len(links)} total links")
    return saved_count


if __name__ == '__main__':
    # Initialize table
    create_table_if_not_exists()
    
    # Create list of all crawl tasks
    tasks = []
    for channel_info in channelIDs:
        for page_num in range(10, 20):
            tasks.append((channel_info, page_num))
    
    # Use ThreadPoolExecutor for parallel crawling
    max_workers = 5  # Adjust based on your needs
    total_saved = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_task = {
            executor.submit(crawl_and_save, task[0], task[1]): task 
            for task in tasks
        }
        
        # Process completed tasks
        for future in as_completed(future_to_task):
            task = future_to_task[future]
            try:
                saved_count = future.result()
                total_saved += saved_count
            except Exception as e:
                channel_info, page_num = task
                print(f"Error crawling {channel_info[1]} page {page_num}: {e}")
    
    print(f"\n=== Crawling Complete ===")
    print(f"Total new URLs saved: {total_saved}")
