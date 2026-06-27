"""
Agent Memory Replay for MultiMind AI.
Allows inspection of each step in an agent workflow.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import json


@dataclass
class AgentStep:
    """Represents a single step in an agent workflow."""
    agent_name: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    timestamp: float
    duration_ms: float = 0
    state_before: Optional[Dict] = None
    state_after: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        return {
            "agent": self.agent_name,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "inputs": self.inputs,
            "outputs": self.outputs,
        }


class WorkflowReplay:
    """
    Captures and replays the reasoning steps in a workflow.
    
    Stores each transition for post-execution analysis.
    """
    
    def __init__(self):
        self.steps: List[AgentStep] = []
    
    def record_step(self, agent_name: str, inputs: Dict, outputs: Dict,
                    state_before: Dict = None, state_after: Dict = None):
        """Record an agent step for replay."""
        import time
        step = AgentStep(
            agent_name=agent_name,
            inputs=inputs,
            outputs=outputs,
            timestamp=time.time(),
            state_before=state_before,
            state_after=state_after,
        )
        self.steps.append(step)
    
    def get_replay(self) -> List[Dict]:
        """Get all recorded steps."""
        return [s.to_dict() for s in self.steps]
    
    def get_step(self, agent_name: str) -> Optional[AgentStep]:
        """Get a specific step by agent name."""
        for s in self.steps:
            if s.agent_name == agent_name:
                return s
        return None
    
    def clear(self):
        """Clear recorded steps."""
        self.steps = []


# Global replay storage
_replays: Dict[str, WorkflowReplay] = {}  # session_id -> WorkflowReplay


def start_replay(session_id: str) -> WorkflowReplay:
    """Start recording a workflow."""
    replay = WorkflowReplay()
    _replays[session_id] = replay
    return replay


def get_replay(session_id: str) -> Optional[WorkflowReplay]:
    """Get replay for a session."""
    return _replays.get(session_id)


def record_step(session_id: str, agent_name: str, inputs: Dict, outputs: Dict,
                state_before: Dict = None, state_after: Dict = None):
    """Record a step for replay."""
    replay = get_replay(session_id)
    if replay:
        replay.record_step(agent_name, inputs, outputs, state_before, state_after)


def get_replay_history(session_id: str) -> List[Dict]:
    """Get replay history for a session."""
    replay = get_replay(session_id)
    return replay.get_replay() if replay else []