#!/usr/bin/env python3
"""
Setup Vector Database from GCS Snapshot
Downloads latest snapshot from GCS and restores to Qdrant
"""
import os
import sys
from google.cloud import storage
from qdrant_client import QdrantClient
from env_config import load_env_config, get_env

# Load environment configuration
load_env_config()

def setup_vectordb():
    """
    Download snapshot from GCS and restore to Qdrant.
    Overwrites existing collection if it exists.
    """
    QDRANT_HOST = get_env('QDRANT_HOST', 'http://127.0.0.1:6333')
    GCS_BUCKET_NAME = get_env('GCS_BUCKET_NAME', 'news_embedding')
    COLLECTION_NAME = get_env('COLLECTION_NAME', 'news_embedding')
    
    # Get credentials path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    credentials_path = os.path.join(current_dir, "..", "keys", "bigquery.json")
    
    print("\n=== Setting up Vector Database ===")
    print(f"   Qdrant Host: {QDRANT_HOST}")
    print(f"   GCS Bucket: {GCS_BUCKET_NAME}")
    print(f"   Collection: {COLLECTION_NAME}")
    
    try:
        # Initialize clients
        qdrant_client = QdrantClient(url=QDRANT_HOST)
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
        
        # Download to temp directory
        temp_dir = '/tmp/qdrant_restore'
        os.makedirs(temp_dir, exist_ok=True)
        local_snapshot = os.path.join(temp_dir, os.path.basename(latest_blob.name))
        
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
        
        # 3. Restore snapshot to Qdrant using file URI
        print(f"\n📤 Restoring snapshot to Qdrant...")
        
        snapshot_uri = f"file://{local_snapshot}"
        qdrant_client.recover_snapshot(
            collection_name=COLLECTION_NAME,
            location=snapshot_uri
        )
        
        print(f"\n✅ Vector database setup complete!")
        print(f"   Collection: {COLLECTION_NAME}")
        print(f"   Snapshot: {latest_blob.name}")
        
        # Cleanup
        os.remove(local_snapshot)
        print(f"   🧹 Cleaned up temporary files")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during vector database setup: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = setup_vectordb()
    sys.exit(0 if success else 1)
