"""RAG chatbot for answering questions about simulation logs.

This module provides a chatbot that uses retrieval-augmented generation
to answer questions about the currently loaded simulation.
"""

import os
from typing import Dict, Any, List, Optional
from openai import OpenAI
from dotenv import load_dotenv
import json

from .vector_store import SimulationVectorStore
from .fact_checker import FactChecker

# Load environment variables from .env file
load_dotenv()


class RAGChatbot:
    """RAG-based chatbot for simulation queries."""
    
    def __init__(self, vector_store: SimulationVectorStore, fact_checker: Optional[FactChecker] = None):
        """Initialize the RAG chatbot.
        
        Args:
            vector_store: Vector store containing simulation chunks
            fact_checker: Optional fact checker for validating answers
        """
        self.vector_store = vector_store
        self.fact_checker = fact_checker
        
        # Initialize OpenAI client (API key loaded from .env)
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found. Set it in .env file or environment variables.")
        
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"  # Cost-effective model
    
    def answer_question(self, question: str, n_results: int = 5) -> Dict[str, Any]:
        """Answer a question about the loaded simulation using RAG.
        
        Args:
            question: User's natural language question
            n_results: Number of relevant chunks to retrieve
            
        Returns:
            Dictionary with answer, sources, confidence, and visualizations
        """
        # Check if vector store has data
        if self.vector_store.count() == 0:
            return {
                'answer': "No simulation data has been loaded yet. Please load a simulation to ask questions about it.",
                'sources': [],
                'confidence': 0.0,
                'visualizations': []
            }
        
        # Retrieve relevant chunks
        relevant_chunks = self.vector_store.search(question, n_results=n_results)
        
        if not relevant_chunks:
            return {
                'answer': "I couldn't find relevant information to answer your question. Please try rephrasing it.",
                'sources': [],
                'confidence': 0.0,
                'visualizations': []
            }
        
        # Build context from retrieved chunks
        context = self._build_context(relevant_chunks)
        
        # Generate answer using LLM
        answer = self._generate_answer(question, context)
        
        # Calculate confidence based on chunk distances
        confidence = self._calculate_confidence(relevant_chunks)
        
        # Suggest visualizations based on question type
        visualizations = self._suggest_visualizations(question, relevant_chunks)
        
        # Validate answer with fact-checker if available
        fact_check = None
        if self.fact_checker:
            try:
                fact_check = self.fact_checker.validate_answer(question, answer)
            except Exception as e:
                print(f"Fact-checking error: {e}")
                # Continue without fact-checking rather than failing
        
        return {
            'answer': answer,
            'sources': [
                {
                    'chunk_type': chunk['metadata'].get('chunk_type', 'unknown'),
                    'relevance': 1.0 - chunk.get('distance', 0.0)  # Convert distance to relevance
                }
                for chunk in relevant_chunks[:3]  # Top 3 sources
            ],
            'confidence': confidence,
            'visualizations': visualizations,
            'fact_check': fact_check
        }
    
    def _build_context(self, chunks: List[Dict]) -> str:
        """Build context string from retrieved chunks."""
        context_parts = []
        
        for i, chunk in enumerate(chunks, 1):
            content = chunk.get('content', '')
            chunk_type = chunk.get('metadata', {}).get('chunk_type', 'unknown')
            context_parts.append(f"[{chunk_type.upper()}] {content}")
        
        return "\n\n".join(context_parts)
    
    def _generate_answer(self, question: str, context: str) -> str:
        """Generate answer using LLM with retrieved context."""
        system_prompt = """You are a helpful assistant for a restaurant manager or chef.
You answer questions about their restaurant simulation in plain, business-friendly language.

Guidelines:
- Use simple language - avoid technical jargon
- Be specific and cite numbers when available
- Focus on actionable insights
- Keep answers concise but complete
- Refer to "this simulation" or "your restaurant"
- Convert technical terms to plain language:
  * RevPASH → "revenue per seat per hour"
  * utilization → "how busy"
  * queue_length → "customers waiting"
  * throughput → "customers served"
"""
        
        user_prompt = f"""Based on the following information about a restaurant simulation, answer this question:

Question: {question}

Simulation Information:
{context}

Please provide a clear, helpful answer for a restaurant manager."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            return f"I encountered an error generating the answer: {str(e)}"
    
    def _calculate_confidence(self, chunks: List[Dict]) -> float:
        """Calculate confidence score based on chunk relevance."""
        if not chunks:
            return 0.0
        
        # Average relevance of top chunks (distance is 0-2, convert to 0-1 confidence)
        distances = [chunk.get('distance', 1.0) for chunk in chunks[:3]]
        avg_distance = sum(distances) / len(distances)
        
        # Convert distance to confidence (lower distance = higher confidence)
        confidence = max(0.0, min(1.0, 1.0 - (avg_distance / 2.0)))
        
        return confidence
    
    def _suggest_visualizations(self, question: str, chunks: List[Dict]) -> List[Dict]:
        """Suggest relevant visualizations based on question type."""
        question_lower = question.lower()
        visualizations = []
        
        # Revenue-related questions
        if any(word in question_lower for word in ['revenue', 'money', 'sales', 'earning']):
            visualizations.append({
                'type': 'revenue_chart',
                'title': 'Revenue Over Time'
            })
        
        # Wait time questions
        if any(word in question_lower for word in ['wait', 'queue', 'waiting', 'long']):
            visualizations.append({
                'type': 'queue_chart',
                'title': 'Queue Lengths Over Time'
            })
            visualizations.append({
                'type': 'service_time_distribution',
                'title': 'Service Time Distribution'
            })
        
        # Station/bottleneck questions
        if any(word in question_lower for word in ['station', 'bottleneck', 'busy', 'grill', 'kitchen']):
            visualizations.append({
                'type': 'station_utilization',
                'title': 'Station Utilization'
            })
        
        # Staffing questions
        if any(word in question_lower for word in ['server', 'cook', 'staff', 'host', 'runner']):
            visualizations.append({
                'type': 'staff_utilization',
                'title': 'Staff Utilization'
            })
        
        # Peak time questions
        if any(word in question_lower for word in ['peak', 'busiest', 'busy', 'when', 'time']):
            visualizations.append({
                'type': 'table_utilization',
                'title': 'Table Utilization Over Time'
            })
        
        return visualizations[:2]  # Return at most 2 suggestions

