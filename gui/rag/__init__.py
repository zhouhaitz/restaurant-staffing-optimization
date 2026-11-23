"""EXPERIMENTAL: RAG (Retrieval-Augmented Generation) system for simulation logs.

This was an exploratory experiment (OpenAI gpt-4o-mini + in-memory ChromaDB over simulation
logs) and is not accurate enough to rely on. Numbers it reports should be checked against the
dashboards. It is optional: the simulator and the rest of the app work without it.

This module provides RAG capabilities for querying simulation data using
vector embeddings and natural language processing.
"""

from .log_processor import LogProcessor
from .vector_store import SimulationVectorStore
from .rag_chatbot import RAGChatbot
from .business_translator import BusinessTranslator
from .fact_checker import FactChecker

__all__ = [
    'LogProcessor',
    'SimulationVectorStore',
    'RAGChatbot',
    'BusinessTranslator',
    'FactChecker',
]

