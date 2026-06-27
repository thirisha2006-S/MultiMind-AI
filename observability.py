"""
Observability Layer for Autonomous Multi-Agent System.

Provides:
- Execution tracing (state before/after each agent)
- State snapshotting and diffing
- Transition auditing
- Invariant enforcement
- Loop detection
- Confidence propagation tracking
"""

import time
import json
import logging
import hashlib
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class TransitionType(Enum):
    """Type of state transition."""
    AGENT_TRANSITION = "agent_transition"
    CONDITIONAL = "conditional"
    LOOP_DETECTED = "loop_detected"
    ERROR = "error"
    TERMINAL = "terminal"


@dataclass
class StateSnapshot:
    """Immutable snapshot of state at a point in time."""
    timestamp: float
    agent: Optional[str]
    state_hash: str
    state_summary: Dict[str, Any]
    transition_type: TransitionType
    message: str = ""
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data["timestamp_iso"] = datetime.fromtimestamp(self.timestamp).isoformat()
        return data


@dataclass
class ExecutionTrace:
    """Complete trace of a single workflow execution."""
    session_id: str
    start_time: float
    end_time: Optional[float] = None
    snapshots: List[StateSnapshot] = field(default_factory=list)
    loop_count: int = 0
    error_count: int = 0
    final_state_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_snapshot(self, snapshot: StateSnapshot):
        self.snapshots.append(snapshot)
    
    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": (self.end_time or time.time()) - self.start_time,
            "snapshots": [s.to_dict() for s in self.snapshots],
            "loop_count": self.loop_count,
            "error_count": self.error_count,
            "final_state_hash": self.final_state_hash,
            "metadata": self.metadata
        }


class InvariantViolation(Exception):
    """Raised when a state invariant is violated."""
    pass


class InvariantChecker:
    """Validates state invariants at transition boundaries."""
    
    @staticmethod
    def compute_state_hash(state: Dict) -> str:
        """Compute stable hash of critical state fields."""
        critical = {
            "messages": len(state.get("messages", [])),
            "current_task_index": state.get("current_task_index", 0),
            "retry_count": state.get("retry_count", 0),
            "planner_ran": state.get("planner_ran", False),
            "research_data_hash": hashlib.md5(str(state.get("research_data", "")).encode()).hexdigest()[:8],
            "code_result_hash": hashlib.md5(str(state.get("code_result", "")).encode()).hexdigest()[:8],
        }
        return hashlib.md5(json.dumps(critical, sort_keys=True).encode()).hexdigest()[:16]
    
    @staticmethod
    def check_field_presence(state: Dict, required_fields: List[str], context: str) -> List[str]:
        """Check that required fields are present and non-null."""
        violations = []
        for field in required_fields:
            if field not in state or state[field] is None:
                violations.append(f"{context}: missing required field '{field}'")
        return violations
    
    @staticmethod
    def check_task_index_bounds(state: Dict) -> List[str]:
        """Check current_task_index is within task_plan bounds (idx <= len is allowed for completion)."""
        violations = []
        idx = state.get("current_task_index", 0)
        plan = state.get("task_plan", [])
        # idx can be in [0, len(plan)] inclusive; -1 or >len invalid
        if plan and (idx < 0 or idx > len(plan)):
            violations.append(f"current_task_index={idx} out of bounds for plan length={len(plan)} (must be 0..len)")
        return violations
    
    @staticmethod
    def check_confidence_range(state: Dict) -> List[str]:
        """Check confidence values are in [0,1]."""
        violations = []
        validation = state.get("validation", {})
        if validation:
            conf = validation.get("confidence")
            if conf is not None and not (0.0 <= conf <= 1.0):
                violations.append(f"validation.confidence={conf} out of range [0,1]")
        reflection = state.get("reflection", {})
        if reflection:
            quality = reflection.get("workflow_quality")
            if quality is not None and not (0.0 <= quality <= 1.0):
                violations.append(f"reflection.workflow_quality={quality} out of range [0,1]")
        return violations
    
    @staticmethod
    def check_retry_limit(state: Dict) -> List[str]:
        """Check retry_count hasn't exceeded max_retries (skip if terminating)."""
        violations = []
        # Allow exceeding max_retries if this is a terminal state (workflow ending)
        if state.get("next") == "END":
            return violations
        retries = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)
        if retries > max_retries:
            violations.append(f"retry_count={retries} exceeds max_retries={max_retries}")
        return violations
    
    @staticmethod
    def check_plan_consistency(state: Dict) -> List[str]:
        """Check planner state is internally consistent."""
        violations = []
        if state.get("planner_ran"):
            plan = state.get("task_plan", [])
            idx = state.get("current_task_index", 0)
            if not plan:
                violations.append("planner_ran=True but task_plan is empty")
            elif idx > len(plan):
                violations.append(f"current_task_index={idx} exceeds plan length={len(plan)}")
        return violations
    
    @staticmethod
    def validate_transition(
        prev_state: Dict, 
        new_state: Dict, 
        agent: str, 
        transition_type: TransitionType = TransitionType.AGENT_TRANSITION
    ) -> List[str]:
        """Run all invariant checks on a state transition."""
        violations = []
        
        # Always-check invariants (global state health)
        violations.extend(InvariantChecker.check_retry_limit(new_state))
        violations.extend(InvariantChecker.check_confidence_range(new_state))
        violations.extend(InvariantChecker.check_task_index_bounds(new_state))
        violations.extend(InvariantChecker.check_plan_consistency(new_state))
        
        # Agent-specific checks only on agent transitions
        if transition_type == TransitionType.AGENT_TRANSITION:
            # Determine if this is a retry (agent returned error and wants to be called again)
            is_retry = bool(new_state.get("error") and new_state.get("next") == agent)
            
            # Only check output field presence if not a retry and not an error
            if not is_retry and not new_state.get("error"):
                if agent == "research":
                    violations.extend(InvariantChecker.check_field_presence(
                        new_state, ["research_data"], f"After {agent}"
                    ))
                elif agent == "coder":
                    violations.extend(InvariantChecker.check_field_presence(
                        new_state, ["code_result"], f"After {agent}"
                    ))
                elif agent == "validator":
                    violations.extend(InvariantChecker.check_field_presence(
                        new_state, ["validation"], f"After {agent}"
                    ))
                elif agent == "reflection":
                    violations.extend(InvariantChecker.check_field_presence(
                        new_state, ["reflection", "final_answer"], f"After {agent}"
                    ))
            
            # Detect potential corruption: same state hash means no progress
            if InvariantChecker.compute_state_hash(prev_state) == InvariantChecker.compute_state_hash(new_state):
                if agent not in ["supervisor", "planner", "validator", "reflection"]:
                    violations.append(f"No state change after {agent} execution (possible infinite loop)")
        
        return violations


class ProgressTracker:
    """Tracks execution progress and detects stuck/looping behavior."""
    
    def __init__(self, max_loops: int = 3):
        self.max_loops = max_loops
        self.agent_visit_counts: Dict[str, int] = {}
        self.state_hashes: List[str] = []
        self.loop_patterns: List[Dict] = []
    
    def record_visit(self, agent: str, state_hash: str) -> bool:
        """
        Record an agent visit.
        Returns True if a loop is detected.
        """
        self.agent_visit_counts[agent] = self.agent_visit_counts.get(agent, 0) + 1
        
        # Detect repeated agent visits without state change
        if len(self.state_hashes) >= 2 and self.state_hashes[-1] == state_hash:
            recent_agents = [s["agent"] for s in self.state_hashes[-2:]]
            if recent_agents[-2:] == [agent, agent]:
                return True  # Same agent twice, no state change
        
        self.state_hashes.append({"agent": agent, "hash": state_hash})
        return False
    
    def get_progress_report(self) -> Dict:
        """Generate progress report."""
        return {
            "agent_visits": dict(self.agent_visit_counts),
            "total_steps": len(self.state_hashes),
            "potential_loops": self.loop_patterns
        }


class ExecutionTracer:
    """
    Central observability hub for the autonomous system.
    
    Captures execution traces, validates invariants, detects loops,
    and provides debugging insights.
    """
    
    def __init__(self, session_id: str, enable_logging: bool = True):
        self.session_id = session_id
        self.trace = ExecutionTrace(session_id=session_id, start_time=time.time())
        self.progress_tracker = ProgressTracker()
        self.enable_logging = enable_logging
        self.invariant_checker = InvariantChecker()
        
        # Configuration
        self.log_interval = 10  # Log every N transitions
        self.transition_count = 0
        
        if self.enable_logging:
            logger.info(f"[Tracer] Started trace for session {session_id}")
    
    def record_transition(
        self,
        agent: str,
        prev_state: Dict,
        new_state: Dict,
        transition_type: TransitionType = TransitionType.AGENT_TRANSITION,
        message: str = ""
    ):
        """Record a state transition with snapshot and validation."""
        self.transition_count += 1
        
        # Compute state hashes
        prev_hash = self.invariant_checker.compute_state_hash(prev_state)
        new_hash = self.invariant_checker.compute_state_hash(new_state)
        
        # Check for loops
        loop_detected = self.progress_tracker.record_visit(agent, new_hash)
        if loop_detected:
            self.trace.loop_count += 1
            logger.warning(f"[Tracer] Loop detected at agent '{agent}' (session={self.session_id})")
        
        # Create snapshot
        snapshot = StateSnapshot(
            timestamp=time.time(),
            agent=agent,
            state_hash=new_hash,
            state_summary=self._summarize_state(new_state),
            transition_type=transition_type,
            message=message or f"Transition from {prev_hash[:8]} to {new_hash[:8]}"
        )
        self.trace.add_snapshot(snapshot)
        
        # Run invariant checks
        violations = self.invariant_checker.validate_transition(
            prev_state, new_state, agent, transition_type
        )
        if violations:
            self.trace.error_count += len(violations)
            for violation in violations:
                logger.error(f"[Tracer] Invariant violation: {violation} (agent={agent})")
        
        # Periodic logging
        if self.enable_logging and self.transition_count % self.log_interval == 0:
            self._log_progress()
    
    def _summarize_state(self, state: Dict) -> Dict:
        """Create condensed summary of state for storage."""
        return {
            "agent": state.get("next", "unknown"),
            "task_index": state.get("current_task_index", 0),
            "retries": state.get("retry_count", 0),
            "has_research": bool(state.get("research_data")),
            "has_code": bool(state.get("code_result")),
            "validated": "validation" in state and state["validation"] is not None,
            "reflected": "reflection" in state and state["reflection"] is not None,
            "confidence": state.get("validation", {}).get("confidence") if state.get("validation") else None,
            "quality": state.get("reflection", {}).get("workflow_quality") if state.get("reflection") else None,
        }
    
    def _log_progress(self):
        """Log current progress."""
        report = self.progress_tracker.get_progress_report()
        logger.info(f"[Tracer] Session={self.session_id} Steps={self.transition_count} "
                   f"Loops={self.trace.loop_count} AgentVisits={report['agent_visits']}")
    
    def finalize(self, final_state: Dict):
        """Mark trace as complete and store final state."""
        self.trace.end_time = time.time()
        self.trace.final_state_hash = self.invariant_checker.compute_state_hash(final_state)
        
        if self.enable_logging:
            duration = self.trace.end_time - self.trace.start_time
            logger.info(f"[Tracer] Session {self.session_id} completed in {duration:.2f}s "
                       f"with {self.transition_count} transitions, {self.trace.error_count} violations")
    
    def get_trace_report(self) -> Dict:
        """Get full trace report for analysis."""
        report = self.trace.to_dict()
        report["progress"] = self.progress_tracker.get_progress_report()
        return report
    
    def export_trace(self, filepath: str):
        """Export trace to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.get_trace_report(), f, indent=2)
        logger.info(f"[Tracer] Trace exported to {filepath}")


# Global registry of active tracers
_active_tracers: Dict[str, ExecutionTracer] = {}


def get_tracer(session_id: str) -> Optional[ExecutionTracer]:
    """Get active tracer for session."""
    return _active_tracers.get(session_id)


def start_trace(session_id: str, **metadata) -> ExecutionTracer:
    """Start a new execution trace."""
    tracer = ExecutionTracer(session_id)
    tracer.trace.metadata.update(metadata)
    _active_tracers[session_id] = tracer
    return tracer


def end_trace(session_id: str, final_state: Dict):
    """End an execution trace."""
    tracer = _active_tracers.get(session_id)
    if tracer:
        tracer.finalize(final_state)
        # Cleanup
        _active_tracers.pop(session_id, None)


def close_trace(session_id: str):
    """Remove trace from registry (call after finalization)."""
    _active_tracers.pop(session_id, None)


def record_transition(
    session_id: str,
    agent: str,
    prev_state: Dict,
    new_state: Dict,
    transition_type: TransitionType = TransitionType.AGENT_TRANSITION,
    message: str = ""
):
    """Record a transition in the active trace."""
    tracer = _active_tracers.get(session_id)
    if tracer:
        tracer.record_transition(agent, prev_state, new_state, transition_type, message)


def trace_agent(agent_name: str):
    """
    Decorator to trace an agent's execution.
    
    Usage:
        @trace_agent("research_agent")
        def research_agent(state: SharedState) -> Dict[str, Any]:
            ...
    """
    def decorator(func: Callable):
        def wrapper(state: Dict):
            session_id = state.get("metadata", {}).get("session_id", "default")
            tracer = get_tracer(session_id)
            
            # Capture pre-state snapshot (shallow copy, will not mutate)
            prev_state = dict(state)
            
            # Execute original agent
            updates = func(state)
            
            # Simulate state merge to see the post-update state
            merged = {}
            # Start with previous state fields
            for k, v in prev_state.items():
                if k == "messages":
                    merged[k] = list(v) if v is not None else []
                else:
                    merged[k] = v
            
            # Apply updates
            for key, value in updates.items():
                if key == "messages":
                    # Extend messages list
                    merged.setdefault("messages", [])
                    if isinstance(value, list):
                        merged["messages"].extend(value)
                    else:
                        merged["messages"].append(value)
                else:
                    merged[key] = value
            
            if tracer:
                tracer.record_transition(
                    agent=agent_name,
                    prev_state=prev_state,
                    new_state=merged,
                    transition_type=TransitionType.AGENT_TRANSITION,
                    message=f"Agent {agent_name} produced updates {list(updates.keys())}"
                )
            return updates
        return wrapper
    return decorator


def trace_routing(router_name: str):
    """
    Decorator to trace routing decisions.
    
    Usage:
        @trace_routing("supervisor")
        def route_from_supervisor(state: SharedState) -> str:
            ...
    """
    def decorator(func: Callable):
        def wrapper(state: Dict):
            session_id = state.get("metadata", {}).get("session_id", "default")
            tracer = get_tracer(session_id)
            
            prev_state = dict(state)
            result = func(state)
            
            if tracer:
                # Create a synthetic new state showing the routing decision
                new_state = dict(prev_state)
                new_state["next"] = result if isinstance(result, str) else "END"
                
                tracer.record_transition(
                    agent=router_name,
                    prev_state=prev_state,
                    new_state=new_state,
                    transition_type=TransitionType.CONDITIONAL,
                    message=f"Routed to '{result}'"
                )
            return result
        return wrapper
    return decorator
