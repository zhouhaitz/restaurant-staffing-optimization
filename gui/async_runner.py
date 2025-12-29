"""Asynchronous simulation runner with progress tracking.

This module provides:
- Thread pool execution for running simulations without blocking UI
- Progress tracking and status updates
- Runtime estimation
- Simulation result management
"""

import streamlit as st
import sys
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, Future
import json
import traceback

# Add experiments directory to path
experiments_path = Path(__file__).parent.parent / "experiments"
sys.path.insert(0, str(experiments_path))

from parameters import SingleDishParameters
# Don't import simulation at module level - import it in the thread function
# to avoid import conflicts with gui/utils.py


class SimulationRunner:
    """Manages asynchronous simulation execution with progress tracking."""
    
    def __init__(self):
        """Initialize simulation runner with thread pool."""
        self.max_workers = 3  # Allow up to 3 simulations in parallel
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        # Initialize session state if needed
        if 'simulation_queue' not in st.session_state:
            st.session_state.simulation_queue = {}
        if 'simulation_futures' not in st.session_state:
            st.session_state.simulation_futures = {}
    
    @staticmethod
    def estimate_runtime(params: SingleDishParameters) -> float:
        """Estimate simulation runtime in seconds.
        
        Formula:
        - Base: 1 second per minute of simulation duration
        - Complexity multiplier based on staffing: (servers + cooks) / 15
        
        Args:
            params: Simulation parameters
        
        Returns:
            Estimated runtime in seconds
        """
        base_time = params.simulation_duration / 60.0
        complexity_multiplier = (params.num_servers + params.num_cooks) / 15.0
        estimated_time = base_time * (1 + complexity_multiplier)
        return estimated_time
    
    @staticmethod
    def validate_parameters(params: SingleDishParameters) -> tuple[bool, Optional[str]]:
        """Validate simulation parameters before running.
        
        Args:
            params: Simulation parameters to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check max duration (3 minutes = 180 minutes simulation time)
        if params.simulation_duration > 180.0:
            return False, "Maximum simulation duration is 3 minutes (180 minutes simulation time)"
        
        # Check minimum staffing
        if params.num_servers < 1 and params.num_hosts < 1 and params.num_cooks < 1:
            return False, "Must have at least some staff configured"
        
        # Check tables
        if not params.table_config or len(params.table_config) == 0:
            return False, "Must have at least one table configured"
        
        return True, None
    
    def _run_simulation_sync(self, params: SingleDishParameters, run_info: Dict) -> Dict:
        """Execute simulation synchronously (runs in thread).
        
        Args:
            params: Simulation parameters
            run_info: Dictionary to update with progress (already in session state)
        
        Returns:
            Dictionary with log data structure
        """
        try:
            # Ensure correct import path for experiments module
            # Remove gui from path to prevent importing gui/utils instead of experiments/utils
            experiments_path = Path(__file__).parent.parent / "experiments"
            experiments_path_str = str(experiments_path)
            gui_path_str = str(Path(__file__).parent)
            
            # Temporarily remove gui from sys.path if present
            gui_was_in_path = False
            if gui_path_str in sys.path:
                sys.path.remove(gui_path_str)
                gui_was_in_path = True
            
            # Ensure experiments is first in path
            if experiments_path_str not in sys.path:
                sys.path.insert(0, experiments_path_str)
            elif sys.path[0] != experiments_path_str:
                sys.path.remove(experiments_path_str)
                sys.path.insert(0, experiments_path_str)
            
            # Clear cached utils module if it's the wrong one (from gui/)
            if 'utils' in sys.modules:
                utils_module = sys.modules['utils']
                if hasattr(utils_module, '__file__') and utils_module.__file__:
                    # Check if it's from gui directory (wrong one)
                    if gui_path_str in utils_module.__file__:
                        # Also clear simulation since it might have imported wrong utils
                        if 'simulation' in sys.modules:
                            del sys.modules['simulation']
                        del sys.modules['utils']
            
            # Import simulation module (will now import correct utils)
            from simulation import RestaurantSimulation
            
            # Restore gui to path if it was there
            if gui_was_in_path and gui_path_str not in sys.path:
                sys.path.append(gui_path_str)
            
            # Update status - modify dict directly (it's already in session state)
            run_info['progress'] = "Initializing simulation..."
            run_info['status'] = "running"
            
            # Create simulation
            sim = RestaurantSimulation(params)
            
            # Update status
            run_info['progress'] = "Running simulation..."
            
            # Run simulation
            results = sim.run()
            
            # Update status
            run_info['progress'] = "Exporting logs..."
            
            # Export to log data structure (compatible with existing data_loader)
            log_data = {
                "metadata": {
                    "simulation_duration": params.simulation_duration,
                    "num_parties": len(sim.parties),
                    "num_dishes": len(sim.all_dishes),
                    "total_revenue": sim.total_revenue,
                    "num_snapshots": len(sim.snapshot_history),
                    "num_events": len(sim.event_log),
                },
                "snapshots": sim.snapshot_history,
                "events": sim.event_log,
            }
            
            # Update status
            run_info['status'] = "complete"
            run_info['progress'] = "Complete!"
            run_info['result'] = log_data
            run_info['metrics'] = results
            run_info['end_time'] = datetime.now()
            
            return log_data
        
        except Exception as e:
            # Handle errors
            error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
            run_info['status'] = "error"
            run_info['progress'] = f"Error: {str(e)}"
            run_info['error'] = error_msg
            run_info['end_time'] = datetime.now()
            raise
    
    def run_simulation_async(self, params: SingleDishParameters, run_id: Optional[str] = None) -> str:
        """Start simulation execution asynchronously.
        
        Args:
            params: Simulation parameters
            run_id: Optional run identifier (auto-generated if not provided)
        
        Returns:
            Run ID for tracking
        """
        # Validate parameters
        is_valid, error_msg = self.validate_parameters(params)
        if not is_valid:
            raise ValueError(error_msg)
        
        # Generate run ID if not provided
        if run_id is None:
            run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Estimate runtime
        estimated_time = self.estimate_runtime(params)
        estimated_end = datetime.now() + timedelta(seconds=estimated_time)
        
        # Initialize run in queue
        run_info = {
            "status": "pending",
            "params": params,
            "progress": "Queued...",
            "start_time": datetime.now(),
            "estimated_end": estimated_end,
            "estimated_duration": estimated_time,
            "result": None,
            "metrics": None,
            "error": None,
            "end_time": None
        }
        st.session_state.simulation_queue[run_id] = run_info
        
        # Submit to thread pool - pass run_info dict (not run_id)
        # The dict is already in session state, so modifying it in thread will update session state
        future = self.executor.submit(self._run_simulation_sync, params, run_info)
        st.session_state.simulation_futures[run_id] = future
        
        return run_id
    
    def get_status(self, run_id: str) -> Optional[Dict]:
        """Get status of a simulation run.
        
        Args:
            run_id: Run identifier
        
        Returns:
            Status dictionary or None if not found
        """
        return st.session_state.simulation_queue.get(run_id)
    
    def cancel_simulation(self, run_id: str) -> bool:
        """Attempt to cancel a running simulation.
        
        Note: Cancellation may not be immediate due to threading limitations.
        
        Args:
            run_id: Run identifier
        
        Returns:
            True if cancellation was attempted, False if not possible
        """
        if run_id in st.session_state.simulation_futures:
            future = st.session_state.simulation_futures[run_id]
            cancelled = future.cancel()
            
            if cancelled:
                st.session_state.simulation_queue[run_id]['status'] = "cancelled"
                st.session_state.simulation_queue[run_id]['progress'] = "Cancelled by user"
                return True
        
        return False
    
    def cleanup_old_runs(self, max_age_hours: int = 24):
        """Clean up old completed runs from session state.
        
        Args:
            max_age_hours: Maximum age in hours to keep runs
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        runs_to_delete = []
        for run_id, run_info in st.session_state.simulation_queue.items():
            if run_info.get('end_time') and run_info['end_time'] < cutoff_time:
                runs_to_delete.append(run_id)
        
        for run_id in runs_to_delete:
            del st.session_state.simulation_queue[run_id]
            if run_id in st.session_state.simulation_futures:
                del st.session_state.simulation_futures[run_id]
    
    def get_active_runs(self) -> Dict[str, Dict]:
        """Get all active (running or pending) simulation runs.
        
        Returns:
            Dictionary of run_id -> run_info for active runs
        """
        active_runs = {}
        for run_id, run_info in st.session_state.simulation_queue.items():
            if run_info['status'] in ['pending', 'running']:
                active_runs[run_id] = run_info
        return active_runs
    
    def get_completed_runs(self) -> Dict[str, Dict]:
        """Get all completed simulation runs.
        
        Returns:
            Dictionary of run_id -> run_info for completed runs
        """
        completed_runs = {}
        for run_id, run_info in st.session_state.simulation_queue.items():
            if run_info['status'] == 'complete':
                completed_runs[run_id] = run_info
        return completed_runs
    
    def save_run_to_disk(self, run_id: str, filepath: str) -> bool:
        """Save simulation run results to disk.
        
        Args:
            run_id: Run identifier
            filepath: Path to save JSON file
        
        Returns:
            True if successful, False otherwise
        """
        run_info = self.get_status(run_id)
        if not run_info or run_info['status'] != 'complete':
            return False
        
        try:
            with open(filepath, 'w') as f:
                json.dump(run_info['result'], f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving run to disk: {e}")
            return False
    
    def __del__(self):
        """Cleanup executor on deletion."""
        try:
            self.executor.shutdown(wait=False)
        except:
            pass


def render_queue_status():
    """Render UI component showing simulation queue status."""
    if 'simulation_queue' not in st.session_state or not st.session_state.simulation_queue:
        st.info("No simulations in queue")
        return
    
    active_runs = {
        run_id: info for run_id, info in st.session_state.simulation_queue.items()
        if info['status'] in ['pending', 'running']
    }
    
    if active_runs:
        st.markdown("### ⏳ Active Simulations")
        for run_id, run_info in active_runs.items():
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.write(f"**{run_id}**")
                    st.write(run_info['progress'])
                
                with col2:
                    status_emoji = "⏸️" if run_info['status'] == 'pending' else "⚙️"
                    st.write(f"{status_emoji} {run_info['status']}")
                
                with col3:
                    elapsed = (datetime.now() - run_info['start_time']).total_seconds()
                    est_total = run_info['estimated_duration']
                    if est_total > 0:
                        progress = min(elapsed / est_total, 1.0)
                        st.progress(progress)
                    st.caption(f"{elapsed:.1f}s / {est_total:.1f}s")
        
        st.markdown("---")
    
    completed_runs = {
        run_id: info for run_id, info in st.session_state.simulation_queue.items()
        if info['status'] in ['complete', 'error', 'cancelled']
    }
    
    if completed_runs:
        st.markdown("### ✅ Completed Simulations")
        for run_id, run_info in list(completed_runs.items())[:5]:  # Show last 5
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.write(f"**{run_id}**")
                    if run_info['status'] == 'complete':
                        st.caption(f"✅ {run_info['progress']}")
                    elif run_info['status'] == 'error':
                        st.caption(f"❌ {run_info['progress']}")
                    else:
                        st.caption(f"🚫 {run_info['progress']}")
                
                with col2:
                    if run_info.get('end_time'):
                        duration = (run_info['end_time'] - run_info['start_time']).total_seconds()
                        st.caption(f"Duration: {duration:.1f}s")
                
                with col3:
                    if run_info['status'] == 'complete':
                        if st.button("Load", key=f"load_{run_id}"):
                            st.session_state.data = run_info['result']
                            st.success("Results loaded!")
                            st.rerun()

