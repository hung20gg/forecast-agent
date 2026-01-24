from google.cloud import bigquery
from google.oauth2 import service_account
import os
from typing import Optional
import asyncio
from env_config import get_env

class BigQueryClient:
    """Client for authenticating and interacting with Google BigQuery."""
    
    def __init__(self, credentials_path:  Optional[str], project_id: Optional[str], limit_time: Optional[str] = None):
        """
        Initialize BigQuery client with authentication.
        
        Args:
            credentials_path: Path to service account JSON credentials file
            project_id: Google Cloud project ID
        """
        self.credentials_path = credentials_path or get_env('GOOGLE_APPLICATION_CREDENTIALS')
        self.project_id = project_id or get_env('GCP_PROJECT_ID')
        self.limit_time = limit_time or get_env('LIMIT_TIME')
        
        if self.credentials_path:

            self.client = bigquery.Client.from_service_account_json(self.credentials_path, project=self.project_id)
        else:
            # Use default credentials (for Cloud environments)
            self.client = bigquery.Client(project=self.project_id)
    
    def get_client(self) -> bigquery.Client:
        """Return the authenticated BigQuery client."""
        return self.client
    
    def test_connection(self) -> bool:
        """Test the BigQuery connection."""
        try:
            list(self.client.list_datasets(max_results=1))
            return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
        
    def execute_query(self, query: str, **kwargs):
        """Execute a SQL query and return the results."""
        query_job = self.client.query(query, **kwargs)
        return query_job.result()
    
    async def aexecute_query(self, query: str, **kwargs):
        """Execute a SQL query asynchronously and return the results."""
        loop = asyncio.get_running_loop()

        def run():
            return self.client.query(query, **kwargs).result()

        return await loop.run_in_executor(None, run)
