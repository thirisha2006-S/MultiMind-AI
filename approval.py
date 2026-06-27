"""
Human Approval Workflow for MultiMind AI Enterprise Knowledge Assistant.

Provides:
- Approval request generation
- Approval/rejection/modify actions
- Pending approval state in LangGraph
- Dashboard integration with Approve/Reject buttons
- Audit trail for approval decisions
"""

import uuid
import json
import logging
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class ApprovalStatus(Enum):
    """Status of an approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    EXPIRED = "expired"


@dataclass
class ApprovalRequest:
    """Represents a human approval request."""
    request_id: str
    session_id: str
    user_id: str
    agent: str
    action: str
    description: str
    proposed_output: str
    context: Dict = field(default_factory=dict)
    status: str = ApprovalStatus.PENDING.value
    created_at: float = field(default_factory=datetime.now().timestamp)
    expires_at: Optional[float] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[float] = None
    review_comment: Optional[str] = None
    modified_output: Optional[str] = None

    def to_dict(self) -> Dict:
        data = asdict(self)
        data["created_at_iso"] = datetime.fromtimestamp(self.created_at).isoformat()
        if self.expires_at:
            data["expires_at_iso"] = datetime.fromtimestamp(self.expires_at).isoformat()
        if self.reviewed_at:
            data["reviewed_at_iso"] = datetime.fromtimestamp(self.reviewed_at).isoformat()
        data["status_enum"] = self.status
        return data


@dataclass
class ApprovalDecision:
    """Represents a decision on an approval request."""
    request_id: str
    decision: str  # "approve", "reject", "modify"
    reviewer_id: str
    comment: Optional[str] = None
    modified_output: Optional[str] = None


class ApprovalManager:
    """Manages human approval workflow."""

    def __init__(self, default_timeout_minutes: int = 60):
        self.requests: Dict[str, ApprovalRequest] = {}
        self.default_timeout = timedelta(minutes=default_timeout_minutes)
        self.rbac = None  # Will be set lazily

    def _get_rbac(self):
        """Lazy-load RBAC manager."""
        if self.rbac is None:
            from rbac import get_rbac_manager
            self.rbac = get_rbac_manager()
        return self.rbac

    def create_request(
        self,
        session_id: str,
        user_id: str,
        agent: str,
        action: str,
        description: str,
        proposed_output: str,
        context: Dict = None,
        timeout_minutes: int = None,
    ) -> ApprovalRequest:
        """
        Create a new approval request.
        
        Args:
            session_id: Current session ID
            user_id: User who triggered the action
            agent: Agent that generated the output
            action: Action requiring approval (e.g., "execute_code", "delete_document")
            description: Human-readable description
            proposed_output: The output to be reviewed
            context: Additional context for the reviewer
            timeout_minutes: Custom timeout (uses default if None)
        
        Returns:
            ApprovalRequest object
        """
        request_id = str(uuid.uuid4())[:8]
        now = datetime.now()
        timeout = timedelta(minutes=timeout_minutes or int(self.default_timeout.total_seconds() / 60))
        
        request = ApprovalRequest(
            request_id=request_id,
            session_id=session_id,
            user_id=user_id,
            agent=agent,
            action=action,
            description=description,
            proposed_output=proposed_output,
            context=context or {},
            expires_at=(now + timeout).timestamp(),
        )
        
        self.requests[request_id] = request
        logger.info(f"[Approval] Request created: {request_id} by user={user_id}, action={action}")
        return request

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get an approval request by ID."""
        return self.requests.get(request_id)

    def get_pending_requests(self, user_id: str = None) -> List[ApprovalRequest]:
        """Get all pending approval requests, optionally filtered by user."""
        pending = []
        for req in self.requests.values():
            if req.status == ApprovalStatus.PENDING.value:
                # Check if expired
                if req.expires_at and datetime.now().timestamp() > req.expires_at:
                    req.status = ApprovalStatus.EXPIRED.value
                else:
                    if user_id is None or req.user_id == user_id:
                        pending.append(req)
        return pending

    def get_user_requests(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get recent approval requests for a user."""
        user_requests = []
        for req in self.requests.values():
            if req.user_id == user_id:
                user_requests.append(req)
        # Sort by created_at descending
        user_requests.sort(key=lambda r: r.created_at, reverse=True)
        return [r.to_dict() for r in user_requests[:limit]]

    def approve(
        self,
        request_id: str,
        reviewer_id: str,
        comment: str = None,
        modified_output: str = None,
    ) -> Optional[ApprovalRequest]:
        """
        Approve an approval request.
        
        Returns:
            Updated ApprovalRequest, or None if not found/invalid
        """
        request = self.requests.get(request_id)
        if not request:
            logger.warning(f"[Approval] Approve failed: request {request_id} not found")
            return None
        
        if request.status != ApprovalStatus.PENDING.value:
            logger.warning(f"[Approval] Approve failed: request {request_id} is not pending (status={request.status})")
            return None
        
        if request.expires_at and datetime.now().timestamp() > request.expires_at:
            request.status = ApprovalStatus.EXPIRED.value
            logger.warning(f"[Approval] Request {request_id} expired before approval")
            return request
        
        # Check if reviewer has permission
        rbac = self._get_rbac()
        reviewer = rbac.get_user(reviewer_id)
        if reviewer and not rbac.can_approve(reviewer, {"resource": "*"}):
            # Allow users to approve their own requests
            if reviewer_id != request.user_id:
                logger.warning(f"[Approval] Reviewer {reviewer_id} lacks approval permission for request {request_id}")
                return None
        
        request.status = ApprovalStatus.APPROVED.value
        request.reviewed_by = reviewer_id
        request.reviewed_at = datetime.now().timestamp()
        request.review_comment = comment
        if modified_output:
            request.modified_output = modified_output
            request.status = ApprovalStatus.MODIFIED.value
        
        logger.info(f"[Approval] Request {request_id} approved by {reviewer_id}")
        return request

    def reject(
        self,
        request_id: str,
        reviewer_id: str,
        comment: str = None,
    ) -> Optional[ApprovalRequest]:
        """
        Reject an approval request.
        
        Returns:
            Updated ApprovalRequest, or None if not found/invalid
        """
        request = self.requests.get(request_id)
        if not request:
            logger.warning(f"[Approval] Reject failed: request {request_id} not found")
            return None
        
        if request.status != ApprovalStatus.PENDING.value:
            logger.warning(f"[Approval] Reject failed: request {request_id} is not pending")
            return None
        
        if request.expires_at and datetime.now().timestamp() > request.expires_at:
            request.status = ApprovalStatus.EXPIRED.value
            return request
        
        request.status = ApprovalStatus.REJECTED.value
        request.reviewed_by = reviewer_id
        request.reviewed_at = datetime.now().timestamp()
        request.review_comment = comment
        
        logger.info(f"[Approval] Request {request_id} rejected by {reviewer_id}")
        return request

    def get_approved_output(self, request_id: str) -> Optional[str]:
        """Get the approved/modified output for a request."""
        request = self.requests.get(request_id)
        if not request:
            return None
        if request.status in [ApprovalStatus.APPROVED.value, ApprovalStatus.MODIFIED.value]:
            return request.modified_output or request.proposed_output
        return None

    def is_approved(self, request_id: str) -> bool:
        """Check if a request has been approved."""
        request = self.requests.get(request_id)
        return request is not None and request.status in [
            ApprovalStatus.APPROVED.value,
            ApprovalStatus.MODIFIED.value,
        ]

    def cleanup_expired(self):
        """Remove expired pending requests."""
        now = datetime.now().timestamp()
        expired_ids = [
            rid for rid, req in self.requests.items()
            if req.expires_at and now > req.expires_at and req.status == ApprovalStatus.PENDING.value
        ]
        for rid in expired_ids:
            self.requests[rid].status = ApprovalStatus.EXPIRED.value
        if expired_ids:
            logger.info(f"[Approval] Cleaned up {len(expired_ids)} expired requests")


# Global approval manager instance
_approval_manager: Optional[ApprovalManager] = None


def get_approval_manager() -> ApprovalManager:
    """Get or create the global approval manager."""
    global _approval_manager
    if _approval_manager is None:
        _approval_manager = ApprovalManager()
    return _approval_manager


def create_approval_request(
    session_id: str,
    user_id: str,
    agent: str,
    action: str,
    description: str,
    proposed_output: str,
    context: Dict = None,
) -> ApprovalRequest:
    """Convenience function to create an approval request."""
    manager = get_approval_manager()
    return manager.create_request(session_id, user_id, agent, action, description, proposed_output, context)


def approve_request(request_id: str, reviewer_id: str, comment: str = None, modified_output: str = None) -> Optional[ApprovalRequest]:
    """Convenience function to approve a request."""
    manager = get_approval_manager()
    return manager.approve(request_id, reviewer_id, comment, modified_output)


def reject_request(request_id: str, reviewer_id: str, comment: str = None) -> Optional[ApprovalRequest]:
    """Convenience function to reject a request."""
    manager = get_approval_manager()
    return manager.reject(request_id, reviewer_id, comment)


def get_approval_status(request_id: str) -> Optional[str]:
    """Convenience function to get approval status."""
    manager = get_approval_manager()
    request = manager.get_request(request_id)
    return request.status if request else None
