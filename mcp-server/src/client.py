from google.cloud import bigquery
from google.oauth2 import service_account
import os


class BigQueryClient:
    """Client for authenticating and interacting with Google BigQuery."""
    
    def __init__(self, credentials_path: str, project_id: str):
        """
        Initialize BigQuery client with authentication.
        
        Args:
            credentials_path: Path to service account JSON credentials file
            project_id: Google Cloud project ID
        """
        self.credentials_path = credentials_path or os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        self.project_id = project_id or os.getenv('GCP_PROJECT_ID')
        
        if self.credentials_path:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=["https://www.googleapis.com/auth/bigquery"]
            )
            self.client = bigquery.Client(
                credentials=credentials,
                project=self.project_id
            )
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