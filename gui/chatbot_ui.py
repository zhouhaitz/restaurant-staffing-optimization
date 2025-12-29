"""Chatbot UI components for Streamlit application.

This module provides UI components for the RAG chatbot interface,
including chat history, contextual suggestions, and response visualizations.
"""

import streamlit as st
from typing import Dict, Any, Optional, List
import sys
import importlib.util
from pathlib import Path
import time

# Add gui directory to path
gui_path = Path(__file__).parent
sys.path.insert(0, str(gui_path))

# Load gui/utils.py explicitly to avoid conflict with experiments/utils.py
gui_utils_path = gui_path / "utils.py"
spec = importlib.util.spec_from_file_location("gui_utils", gui_utils_path)
gui_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gui_utils)

from rag import RAGChatbot
from visualizations import (
    plot_revenue_accumulation,
    plot_queue_lengths,
    plot_station_utilization,
    plot_staff_utilization,
    plot_table_utilization,
    plot_service_time_distribution
)
from metrics_calculator import (
    calculate_revpash,
    calculate_queue_metrics,
    calculate_station_utilization,
    calculate_staff_utilization,
    calculate_table_utilization,
    calculate_service_times
)

# Import from gui_utils to avoid conflict
get_total_seats_from_snapshots = gui_utils.get_total_seats_from_snapshots
get_total_tables_from_snapshots = gui_utils.get_total_tables_from_snapshots


def render_chatbot_tab():
    """Render the main chatbot interface tab."""
    # Check if simulation is loaded
    if 'data' not in st.session_state or st.session_state.data is None:
        st.info("👈 Please load a simulation to start asking questions.")
        st.markdown("""
        ### What you can ask:
        
        Once you load a simulation, you can ask questions like:
        - "How much revenue did we make?"
        - "What was our average wait time?"
        - "Which station was our biggest bottleneck?"
        - "What time were we busiest?"
        - "How busy were our servers?"
        
        The chatbot will analyze your simulation and provide business-friendly answers with fact-checking.
        """)
        return
    
    # Check if RAG chatbot is initialized
    if 'rag_chatbot' not in st.session_state or st.session_state.rag_chatbot is None:
        st.warning("⚠️ Chatbot is initializing. Please wait a moment and refresh.")
        return
    
    # Initialize chat history
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Display chat history FIRST (so newest messages are visible)
    render_chat_history()
    
    # Chat input at bottom (Streamlit automatically places this at bottom)
    user_question = st.chat_input("Ask a question about your simulation...")
    
    # Process question
    if user_question:
        # Add user message to history
        st.session_state.chat_history.append({
            'role': 'user',
            'content': user_question
        })
        
        # Get answer from RAG chatbot
        with st.spinner("Thinking..."):
            response = st.session_state.rag_chatbot.answer_question(user_question)
        
        # Add assistant response to history
        st.session_state.chat_history.append({
            'role': 'assistant',
            'content': response,
            'question': user_question  # Store question for context
        })
        
        st.rerun()


def render_answer_with_fact_check(answer: str, fact_check: Optional[Dict]) -> str:
    """Return the answer without inline modifications.
    
    Fact-check information is displayed separately in a summary card below the answer
    for better readability.
    
    Args:
        answer: The answer text
        fact_check: Fact-check results dictionary (used elsewhere, not here)
        
    Returns:
        Original answer text without modifications
    """
    return answer


def generate_suggested_queries(answer: str, question: str, fact_check: Optional[Dict] = None) -> List[str]:
    """Generate contextual follow-up questions based on the answer.
    
    Args:
        answer: The chatbot's answer
        question: The original question
        fact_check: Optional fact-check results
        
    Returns:
        List of 2-3 suggested follow-up questions
    """
    suggestions = []
    answer_lower = answer.lower()
    question_lower = question.lower()
    
    # Revenue-related suggestions
    if 'revenue' in answer_lower:
        if 'party' not in question_lower:
            suggestions.append("What was the revenue per party?")
        if 'hour' not in question_lower:
            suggestions.append("How much revenue per hour did we generate?")
    
    # Party/customer suggestions
    if 'part' in answer_lower or 'customer' in answer_lower:
        if 'wait' not in question_lower:
            suggestions.append("What was the average wait time?")
        suggestions.append("How many parties did we serve per hour?")
    
    # Station/bottleneck suggestions
    if 'station' in answer_lower or 'bottleneck' in answer_lower or 'busy' in answer_lower:
        suggestions.append("What was the utilization of other stations?")
        suggestions.append("Which station had the longest queue?")
    
    # Utilization suggestions
    if 'utilization' in answer_lower or 'busy' in answer_lower:
        if 'table' in answer_lower:
            suggestions.append("How busy were our servers?")
        if 'staff' in answer_lower or 'server' in answer_lower:
            suggestions.append("What was our table utilization?")
    
    # Time-based suggestions
    if 'time' in answer_lower or 'peak' in answer_lower:
        suggestions.append("What was happening at the busiest time?")
        suggestions.append("How did performance change throughout service?")
    
    # If no specific suggestions, provide general ones
    if not suggestions:
        suggestions = [
            "What was the biggest bottleneck?",
            "How can we improve performance?",
            "What was our peak time?"
        ]
    
    # Return 2-3 unique suggestions
    unique_suggestions = []
    for s in suggestions:
        if s not in unique_suggestions and s.lower() != question_lower:
            unique_suggestions.append(s)
        if len(unique_suggestions) >= 3:
            break
    
    return unique_suggestions[:3]


def render_chat_history():
    """Display the conversation history with ChatGPT-style bubbles."""
    if 'chat_history' not in st.session_state or not st.session_state.chat_history:
        st.info("💭 Ask a question below to get started!")
        return
    
    # Display each message
    for i, chat in enumerate(st.session_state.chat_history):
        if chat['role'] == 'user':
            # User message
            with st.chat_message("user"):
                st.markdown(chat['content'])
        
        else:
            # Assistant message
            with st.chat_message("assistant"):
                response = chat['content']
                
                # Extract response components
                if isinstance(response, dict):
                    answer = response.get('answer', '')
                    fact_check = response.get('fact_check')
                    sources = response.get('sources', [])
                    confidence = response.get('confidence', 0)
                    visualizations = response.get('visualizations', [])
                else:
                    answer = response
                    fact_check = None
                    sources = []
                    confidence = 0
                    visualizations = []
                
                # Display answer (clean, no inline badges)
                st.markdown(answer)
                
                # Fact-check summary card (if available) - subtle and informative
                if fact_check and fact_check.get('verified_count', 0) > 0:
                    render_fact_check_summary_card(fact_check)
                
                # Sources in fine print
                if sources:
                    source_types = [s.get('chunk_type', 'unknown').title() for s in sources[:2]]
                    st.caption(f"📚 Sources: {', '.join(source_types)}")
                
                # Visualizations (if any) - with better spacing
                if visualizations:
                    st.markdown("")  # Add spacing
                    render_response_visualizations(visualizations, i)
                
                # Suggested follow-up questions
                question = chat.get('question', '')
                if question:
                    suggested = generate_suggested_queries(answer, question, fact_check)
                    if suggested:
                        st.markdown("")  # Add spacing
                        cols = st.columns(len(suggested))
                        for col, suggestion in zip(cols, suggested):
                            with col:
                                if st.button(suggestion, key=f"suggest_{i}_{suggestion[:20]}", use_container_width=True):
                                    # Add to chat history
                                    st.session_state.chat_history.append({
                                        'role': 'user',
                                        'content': suggestion
                                    })
                                    
                                    with st.spinner("Thinking..."):
                                        response = st.session_state.rag_chatbot.answer_question(suggestion)
                                    
                                    st.session_state.chat_history.append({
                                        'role': 'assistant',
                                        'content': response,
                                        'question': suggestion
                                    })
                                    
                                    st.rerun()
                
                # Expandable details (sources and fact-check) - minimal
                if (sources or (fact_check and fact_check.get('validated_claims'))):
                    with st.expander("📋 Details", expanded=False):
                        if sources:
                            st.caption("**Sources:**")
                            for source in sources:
                                chunk_type = source.get('chunk_type', 'unknown')
                                relevance = source.get('relevance', 0)
                                st.caption(f"• {chunk_type.title()} ({relevance:.0%})")
                        
                        if fact_check and fact_check.get('validated_claims'):
                            st.caption("")
                            st.caption("**Fact Check Breakdown:**")
                            render_fact_check_details(fact_check)
                            
                            # Show individual claims
                            st.caption("")
                            st.caption("**Claims Validated:**")
                            for val in fact_check.get('validated_claims', [])[:5]:  # Show up to 5
                                claim = val.claim
                                badge = val.badge
                                level = val.accuracy_level
                                
                                if val.ground_truth is not None:
                                    error_pct = (val.error * 100) if val.error else 0
                                    st.caption(
                                        f"{badge} {str(claim)} → {level} "
                                        f"(actual: {val.ground_truth:.1f}, error: {error_pct:.1f}%)"
                                    )
                                else:
                                    st.caption(f"{badge} {str(claim)} → {level}")


def render_fact_check_summary_card(fact_check: Dict):
    """Render a subtle fact-check summary card below the answer.
    
    Args:
        fact_check: Fact-check results dictionary
    """
    if not fact_check:
        return
    
    accurate = fact_check.get('accurate_count', 0)
    approximate = fact_check.get('approximate_count', 0)
    inaccurate = fact_check.get('inaccurate_count', 0)
    unverified = fact_check.get('unverified_count', 0)
    total = fact_check.get('verified_count', 0)
    overall_accuracy = fact_check.get('overall_accuracy', 0)
    
    # Determine overall status
    if overall_accuracy >= 0.9:
        status_icon = "✅"
        status_text = "Verified"
        status_color = "#10b981"  # green
    elif overall_accuracy >= 0.7:
        status_icon = "✓"
        status_text = "Mostly Accurate"
        status_color = "#10b981"  # green
    elif overall_accuracy >= 0.5:
        status_icon = "⚠️"
        status_text = "Partially Verified"
        status_color = "#f59e0b"  # amber
    else:
        status_icon = "⚠️"
        status_text = "Needs Review"
        status_color = "#ef4444"  # red
    
    # Create a subtle card-like display
    st.markdown(f"""
    <div style="
        background-color: rgba(0, 0, 0, 0.02);
        border-left: 3px solid {status_color};
        padding: 8px 12px;
        margin: 8px 0;
        border-radius: 4px;
        font-size: 0.875rem;
    ">
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 1.1rem;">{status_icon}</span>
            <span style="font-weight: 500; color: {status_color};">{status_text}</span>
            <span style="color: #6b7280; margin-left: auto;">
                {accurate} accurate, {approximate} approx, {inaccurate} inaccurate of {total} checked
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_fact_check_details(fact_check: Dict):
    """Render detailed fact-check breakdown in fine print.
    
    Args:
        fact_check: Fact-check results dictionary
    """
    if not fact_check:
        return
    
    # Breakdown by accuracy (concise)
    accurate = fact_check.get('accurate_count', 0)
    approximate = fact_check.get('approximate_count', 0)
    inaccurate = fact_check.get('inaccurate_count', 0)
    
    if accurate > 0:
        st.caption(f"✓ {accurate} accurate")
    if approximate > 0:
        st.caption(f"⚠ {approximate} approximate")
    if inaccurate > 0:
        st.caption(f"✗ {inaccurate} inaccurate")


def render_response_visualizations(visualizations: list, message_index: int):
    """Render visualizations suggested by the chatbot with better spacing.
    
    Args:
        visualizations: List of visualization dictionaries
        message_index: Index of the message (for unique keys)
    """
    if not visualizations:
        return
    
    # Get data from session state
    data = st.session_state.data
    snapshots = data.get('snapshots', [])
    
    if not snapshots:
        st.caption("No snapshot data available for visualizations.")
        return
    
    # Calculate metrics as needed
    total_seats = get_total_seats_from_snapshots(snapshots)
    
    # Add spacing before charts
    st.markdown("**Related Charts:**")
    
    for viz_idx, viz in enumerate(visualizations[:2]):  # Show at most 2 visualizations
        viz_type = viz.get('type', '')
        title = viz.get('title', '')
        
        # Add spacing between charts
        if viz_idx > 0:
            st.markdown("")
        
        try:
            # Use unique key based on message index, viz index, and timestamp
            unique_key = f"viz_{viz_type}_{message_index}_{viz_idx}_{int(time.time() * 1000)}"
            
            if viz_type == 'revenue_chart':
                revpash_df = calculate_revpash(snapshots, total_seats)
                st.plotly_chart(
                    plot_revenue_accumulation(revpash_df),
                    use_container_width=True,
                    key=unique_key
                )
            
            elif viz_type == 'queue_chart':
                queue_df = calculate_queue_metrics(snapshots)
                st.plotly_chart(
                    plot_queue_lengths(queue_df),
                    use_container_width=True,
                    key=unique_key
                )
            
            elif viz_type == 'station_utilization':
                station_util_df = calculate_station_utilization(snapshots)
                st.plotly_chart(
                    plot_station_utilization(station_util_df),
                    use_container_width=True,
                    key=unique_key
                )
            
            elif viz_type == 'staff_utilization':
                staff_util_df = calculate_staff_utilization(snapshots)
                st.plotly_chart(
                    plot_staff_utilization(staff_util_df),
                    use_container_width=True,
                    key=unique_key
                )
            
            elif viz_type == 'table_utilization':
                total_tables = get_total_tables_from_snapshots(snapshots)
                table_util_df = calculate_table_utilization(snapshots, total_tables)
                st.plotly_chart(
                    plot_table_utilization(table_util_df),
                    use_container_width=True,
                    key=unique_key
                )
            
            elif viz_type == 'service_time_distribution':
                service_times = calculate_service_times(snapshots)
                st.plotly_chart(
                    plot_service_time_distribution(service_times),
                    use_container_width=True,
                    key=unique_key
                )
        
        except Exception as e:
            st.caption(f"Could not generate {title}: {str(e)}")


