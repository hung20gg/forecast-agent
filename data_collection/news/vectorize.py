from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, HnswConfigDiff

from google.cloud import bigquery
from datetime import timezone
import os
import requests
from typing import Union
import time
import hashlib

KEY_PATH = os.path.join(os.path.dirname(__file__), '../keys/big-query.json')

# Update these with your project and dataset
EMBEDDING_URL = 'http://127.0.0.1:8080/embed'
QDRANT_HOST = 'http://127.0.0.1:6333'
PROJECT_ID = 'neusolution'
DATASET_ID = 'ktln'
TABLE_ID = 'news'
TABLE_FULL_ID = f'{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}'


bq_client = bigquery.Client.from_service_account_json(KEY_PATH)
qdrant_client = QdrantClient(url=QDRANT_HOST)

collection_name = "news_embedding"
if not qdrant_client.collection_exists(collection_name):
    # Create collection with sparse HNSW configuration
    qdrant_client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=768,
            distance=Distance.COSINE,
            hnsw_config=HnswConfigDiff(
                m=16,  # Number of edges per node
                ef_construct=100,  # Size of the dynamic candidate list
                full_scan_threshold=10000  # Threshold for switching to full scan
            )
        )
    )
    print(f"Collection '{collection_name}' created successfully!")
else:
    print(f"Collection '{collection_name}' already exists.")

query_tpl = """
    SELECT
    url,
    title,
    text,
    pub_date
    FROM `{table_full_id}`
    WHERE (vectorized IS NULL OR vectorized = FALSE)
    AND text IS NOT NULL
    ORDER BY pub_date
    LIMIT {limit}
"""
BATCH_SIZE = 1
EMBEDDING_BATCH_SIZE = 1


def split_text_into_chunks(text: str, chunk_size: int = 1024) -> list[str]:
    """
    Split text into chunks of specified word count with 1 sentence overlap.
    """
    import re
    
    # Split text into sentences (basic sentence splitting)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    chunks = []
    current_chunk = []
    current_word_count = 0
    overlap_sentence = None
    
    for sentence in sentences:
        sentence_words = len(sentence.split())
        
        # If adding this sentence would exceed chunk size, save current chunk
        if current_word_count + sentence_words > chunk_size and current_chunk:
            # Save the chunk
            chunks.append(' '.join(current_chunk))
            
            # Start new chunk with last sentence as overlap
            overlap_sentence = current_chunk[-1]
            current_chunk = [overlap_sentence, sentence]
            current_word_count = len(overlap_sentence.split()) + sentence_words
        else:
            current_chunk.append(sentence)
            current_word_count += sentence_words
    
    # Add the last chunk if it exists
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    # Return only first 3 chunks and last 2 chunks to limit total chunks
    if len(chunks) > 5:
        return chunks[:3] + chunks[-2:]
    
    return chunks if chunks else [text]


def get_embedding(query: Union[str, list[str]]) -> list[float]:
    """
    curl 127.0.0.1:8080/embed \
    -X POST \
    -d '{"inputs":"What is Deep Learning?"}' \
    -H 'Content-Type: application/json'
    """

    response = requests.post(
        EMBEDDING_URL,
        json={"inputs": query},
        headers={"Content-Type": "application/json"}
    )
    response.raise_for_status()
    embedding = response.json()
    return embedding


while True:
    query = query_tpl.format(table_full_id = TABLE_FULL_ID, limit=BATCH_SIZE)
    rows = list(bq_client.query(query).result())

    if not rows:
        break

    # Process texts with chunking
    ids = []
    payloads = []
    all_chunks = []
    
    for r in rows:
        chunks = split_text_into_chunks(r.text, chunk_size=1024)
        for chunk_idx, chunk in enumerate(chunks):
            # Generate UUID from URL and chunk index for Qdrant
            chunk_identifier = f"{r.url}#chunk{chunk_idx}"
            # Create a deterministic UUID using MD5 hash
            chunk_uuid = hashlib.md5(chunk_identifier.encode()).hexdigest()
            
            ids.append(chunk_uuid)
            payloads.append({
                "url": r.url,
                "title": r.title,
                "chunk_index": chunk_idx,
                "total_chunks": len(chunks),
                "chunk_identifier": chunk_identifier,
                "pub_date": int(r.pub_date.replace(tzinfo=timezone.utc).timestamp())
            })
            all_chunks.append(chunk)
    
    # Get embeddings for all chunks
    embeddings = []
    for i in range(0, len(all_chunks), EMBEDDING_BATCH_SIZE):
        batch_texts = all_chunks[i:i+EMBEDDING_BATCH_SIZE]
        batch_embeddings = get_embedding(batch_texts)
        embeddings.extend(batch_embeddings)
        print(f"Processed {len(embeddings)}/{len(all_chunks)} chunk embeddings")
        time.sleep(0.1)  # To avoid overwhelming the embedding service

    qdrant_client.upload_collection(
        collection_name=collection_name,
        ids=ids,
        vectors=embeddings,
        payload=payloads,
        batch_size=256
    )

    # Mark vectorized
    # Extract unique URLs from chunk IDs
    unique_urls = list(set([r.url for r in rows]))
    
    update_query = f"""
    UPDATE `{TABLE_FULL_ID}`
    SET vectorized = TRUE
    WHERE url IN UNNEST(@urls)
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter(
                "urls", "STRING", unique_urls
            )
        ]
    )

    bq_client.query(update_query, job_config=job_config).result()

    print(f"Done {len(unique_urls)} articles ({len(ids)} chunks)")