#!/usr/bin/env python3
"""
Setup Vector Database from GCS Snapshot
Downloads latest snapshot from GCS and restores to Qdrant
"""
import os
import sys
from google.cloud import storage
from qdrant_client import QdrantClient
from dotenv import load_dotenv
# Load environment configuration
load_dotenv()

def setup_vectordb():
    """
    Download snapshot from GCS and restore to Qdrant.
    Overwrites existing collection if it exists.
    """
    if os.getenv("ALLOW_VECTORDB_RESET", "false").lower() != "true":
        print("Refusing to reset vector DB. Set ALLOW_VECTORDB_RESET=true to proceed.")
        return False
    QDRANT_URL = os.getenv('QDRANT_URL', 'http://qdrant:6333')
    GCS_BUCKET_NAME = os.getenv('GCS_BUCKET_NAME', 'news_embedding')
    COLLECTION_NAME = os.getenv('COLLECTION_NAME', 'news_embedding')
    
    
    
    # Get credentials path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    credentials_path = str(os.getenv('GCS_CREDENTIALS_PATH'))
    
    # Verify credentials file exists
    if not os.path.isfile(credentials_path):
        raise FileNotFoundError(
            f"GCS credentials not found at {credentials_path}"
        )
    
    print("\n=== Setting up Vector Database ===")
    print(f"   Qdrant Host: {QDRANT_URL}")
    print(f"   GCS Bucket: {GCS_BUCKET_NAME}")
    print(f"   Collection: {COLLECTION_NAME}")
    
    try:
        # Initialize clients
        qdrant_client = QdrantClient(url=QDRANT_URL)
        storage_client = storage.Client.from_service_account_json(credentials_path)
        
        # 1. Download latest snapshot from GCS
        print(f"\n📥 Downloading snapshot from gs://{GCS_BUCKET_NAME}...")
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        
        # Get latest snapshot (assuming naming: news_embedding_YYYYMMDD.snapshot)
        blobs = list(bucket.list_blobs(prefix='qdrant_snapshots/'))
        if not blobs:
            print("❌ No snapshots found in GCS bucket")
            return False
        
        # Sort by name to get latest date
        latest_blob = sorted(blobs, key=lambda x: x.name, reverse=True)[0]
        print(f"   Found: {latest_blob.name}")
        
        # Download to shared snapshots directory
        temp_dir = '/qdrant/snapshots'
        os.makedirs(temp_dir, exist_ok=True)
        local_snapshot = os.path.join(temp_dir, os.path.basename(latest_blob.name)).replace('\\', '/')
        
        latest_blob.download_to_filename(local_snapshot)
        file_size_mb = os.path.getsize(local_snapshot) / (1024 * 1024)
        print(f"   Downloaded to: {local_snapshot} ({file_size_mb:.2f} MB)")
        
        # 2. Delete existing collection if it exists
        try:
            if qdrant_client.collection_exists(COLLECTION_NAME):
                print(f"\n🗑️  Deleting existing collection: {COLLECTION_NAME}")
                qdrant_client.delete_collection(COLLECTION_NAME)
                print(f"   Deleted successfully")
        except Exception as e:
            print(f"⚠️  Warning during collection deletion: {e}")
        
        # 3. Restore snapshot to Qdrant using Qdrant's direct recover API
        print(f"\n📤 Recovering snapshot in Qdrant from shared volume...")
        
        import requests
        url = f"{QDRANT_URL}/collections/{COLLECTION_NAME}/snapshots/recover?wait=true"
        payload = {
            "location": f"file:///qdrant/snapshots/{os.path.basename(local_snapshot)}"
        }
        resp = requests.put(url, json=payload)
        if resp.status_code not in [200, 201, 202]:
            raise Exception(f"Snapshot recovery failed: {resp.status_code} - {resp.text}")
        
        print(f"\n✅ Vector database setup complete!")
        print(f"   Collection: {COLLECTION_NAME}")
        print(f"   Snapshot: {latest_blob.name}")
        
        # Cleanup
        os.remove(local_snapshot)
        print(f"   🧹 Cleaned up temporary files")
        
        # 4. Create index on pub_date field
        print(f"\n🔍 Creating index on pub_date field...")
        index_url = f"{QDRANT_URL}/collections/{COLLECTION_NAME}/index"
        index_payload = {
            "field_name": "pub_date",
            "field_schema": "integer"
        }
        index_resp = requests.put(index_url, json=index_payload)
        if index_resp.status_code not in [200, 201]:
            print(f"⚠️  Warning: Index creation returned {index_resp.status_code} - {index_resp.text}")
        else:
            print(f"   ✅ Index created on pub_date")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during vector database setup: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = setup_vectordb()
    sys.exit(0 if success else 1)
