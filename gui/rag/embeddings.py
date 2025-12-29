"""Embedding generation utilities for RAG system.

This module provides utilities for generating embeddings from text,
with support for OpenAI and local models.
"""

import os
from typing import List
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class EmbeddingGenerator:
    """Generate embeddings for text chunks."""
    
    def __init__(self, model: str = "text-embedding-3-small"):
        """Initialize embedding generator.
        
        Args:
            model: OpenAI embedding model to use
        """
        self.model = model
        self.client = None
        
        # Load API key from environment (checks .env file via load_dotenv)
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.client = OpenAI(api_key=api_key)
    
    def generate(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        if not self.client:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY in .env file or environment variables.")
        
        if not texts:
            return []
        
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts
            )
            
            embeddings = [item.embedding for item in response.data]
            return embeddings
        
        except Exception as e:
            print(f"Error generating embeddings: {e}")
            return []

