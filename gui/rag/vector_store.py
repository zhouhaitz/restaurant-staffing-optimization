"""Vector store for simulation log embeddings using ChromaDB.

This module manages an in-memory vector database for storing and retrieving
simulation log chunks using semantic search.
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any
import json


class SimulationVectorStore:
    """In-memory vector store for simulation log chunks."""
    
    def __init__(self):
        """Initialize in-memory ChromaDB client."""
        # Create in-memory client (no persistence)
        self.client = chromadb.Client(Settings(
            is_persistent=False,
            anonymized_telemetry=False
        ))
        
        # Create or get collection
        self.collection = self.client.get_or_create_collection(
            name="current_simulation",
            metadata={"hnsw:space": "cosine"}
        )
        
        self._chunk_counter = 0
    
    def clear(self):
        """Clear all chunks from the vector store."""
        try:
            # Delete the collection
            self.client.delete_collection("current_simulation")
            
            # Recreate it
            self.collection = self.client.get_or_create_collection(
                name="current_simulation",
                metadata={"hnsw:space": "cosine"}
            )
            
            self._chunk_counter = 0
        except Exception as e:
            print(f"Error clearing vector store: {e}")
    
    def add_log_chunks(self, chunks: List[Dict[str, Any]]):
        """Add processed log chunks to the vector store.
        
        Args:
            chunks: List of chunk dictionaries with 'content' and 'metadata'
        """
        if not chunks:
            return
        
        # Prepare data for ChromaDB
        documents = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            # Extract content
            content = chunk.get('content', '')
            if not content:
                continue
            
            documents.append(content)
            
            # Convert metadata to string values (ChromaDB requirement)
            metadata = chunk.get('metadata', {})
            serialized_metadata = {
                'chunk_type': str(metadata.get('chunk_type', 'unknown')),
                'metrics': json.dumps(metadata.get('metrics', {})),
                'time_range': json.dumps(metadata.get('time_range', []))
            }
            metadatas.append(serialized_metadata)
            
            # Generate unique ID
            chunk_id = f"chunk_{self._chunk_counter}_{i}"
            ids.append(chunk_id)
        
        # Add to collection (ChromaDB handles embedding generation)
        if documents:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            self._chunk_counter += len(documents)
    
    def search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant chunks using semantic similarity.
        
        Args:
            query: User's natural language question
            n_results: Number of results to return
            
        Returns:
            List of relevant chunks with content, metadata, and similarity scores
        """
        try:
            # Query the collection
            results = self.collection.query(
                query_texts=[query],
                n_results=min(n_results, self._chunk_counter) if self._chunk_counter > 0 else 1
            )
            
            # Format results
            chunks = []
            if results and results['documents'] and len(results['documents']) > 0:
                for i, doc in enumerate(results['documents'][0]):
                    chunk = {
                        'content': doc,
                        'metadata': {},
                        'distance': results['distances'][0][i] if 'distances' in results else 0.0
                    }
                    
                    # Deserialize metadata
                    if results['metadatas'] and len(results['metadatas']) > 0:
                        raw_meta = results['metadatas'][0][i]
                        chunk['metadata'] = {
                            'chunk_type': raw_meta.get('chunk_type', 'unknown'),
                            'metrics': json.loads(raw_meta.get('metrics', '{}')),
                            'time_range': json.loads(raw_meta.get('time_range', '[]'))
                        }
                    
                    chunks.append(chunk)
            
            return chunks
        
        except Exception as e:
            print(f"Error searching vector store: {e}")
            return []
    
    def count(self) -> int:
        """Get the number of chunks in the store."""
        return self._chunk_counter

