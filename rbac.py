"""
Role-Based Access Control (RBAC) for MultiMind AI Enterprise Knowledge Assistant.

Provides:
- Role definitions (admin, employee, customer)
- Permission checks for agents, documents, and actions
- Resource-level access control
- Session-aware permission enforcement
"""

import json
import logging
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class Role(Enum):
    """Enumeration of available roles."""
    ADMIN = "admin"
    EMPLOYEE = "employee"
    CUSTOMER = "customer"
    GUEST = "guest"


class Action(Enum):
    """Enumeration of available actions."""
    # Document actions
    UPLOAD_DOCUMENT = "upload_document"
    VIEW_DOCUMENT = "view_document"
    DELETE_DOCUMENT = "delete_document"
    EDIT_DOCUMENT = "edit_document"
    # Query actions
    RESEARCH_PUBLIC = "research_public"
    RESEARCH_PRIVATE = "research_private"
    EXECUTE_CODE = "execute_code"
    # Approval actions
    APPROVE_ACTION = "approve_action"
    REJECT_ACTION = "reject_action"
    # Admin actions
    MANAGE_USERS = "manage_users"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    VIEW_ANALYTICS = "view_analytics"
    MANAGE_ROLES = "manage_roles"
    # Feedback actions
    SUBMIT_FEEDBACK = "submit_feedback"
    VIEW_FEEDBACK = "view_feedback"


@dataclass
class Permission:
    """Represents a permission grant."""
    action: str
    resource: str  # "*" for all, or specific resource type
    conditions: Dict = field(default_factory=dict)


@dataclass
class User:
    """Represents a user in the system."""
    user_id: str
    username: str
    role: str
    department: Optional[str] = None
    allowed_document_categories: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


# Default role-permission mapping
# Format: role -> list of Permission objects
ROLE_PERMISSIONS: Dict[str, List[Permission]] = {
    Role.ADMIN.value: [
        Permission(Action.UPLOAD_DOCUMENT.value, "*"),
        Permission(Action.VIEW_DOCUMENT.value, "*"),
        Permission(Action.DELETE_DOCUMENT.value, "*"),
        Permission(Action.EDIT_DOCUMENT.value, "*"),
        Permission(Action.RESEARCH_PUBLIC.value, "*"),
        Permission(Action.RESEARCH_PRIVATE.value, "*"),
        Permission(Action.EXECUTE_CODE.value, "*"),
        Permission(Action.APPROVE_ACTION.value, "*"),
        Permission(Action.REJECT_ACTION.value, "*"),
        Permission(Action.MANAGE_USERS.value, "*"),
        Permission(Action.VIEW_AUDIT_LOGS.value, "*"),
        Permission(Action.VIEW_ANALYTICS.value, "*"),
        Permission(Action.MANAGE_ROLES.value, "*"),
        Permission(Action.SUBMIT_FEEDBACK.value, "*"),
        Permission(Action.VIEW_FEEDBACK.value, "*"),
    ],
    Role.EMPLOYEE.value: [
        Permission(Action.UPLOAD_DOCUMENT.value, "department:{department}"),
        Permission(Action.VIEW_DOCUMENT.value, "department:{department},public"),
        Permission(Action.DELETE_DOCUMENT.value, "department:{department}"),
        Permission(Action.EDIT_DOCUMENT.value, "department:{department}"),
        Permission(Action.RESEARCH_PUBLIC.value, "*"),
        Permission(Action.RESEARCH_PRIVATE.value, "department:{department}"),
        Permission(Action.EXECUTE_CODE.value, "sandbox"),
        Permission(Action.APPROVE_ACTION.value, "own"),
        Permission(Action.REJECT_ACTION.value, "own"),
        Permission(Action.SUBMIT_FEEDBACK.value, "*"),
        Permission(Action.VIEW_FEEDBACK.value, "own"),
    ],
    Role.CUSTOMER.value: [
        Permission(Action.VIEW_DOCUMENT.value, "public,customer:{customer_id}"),
        Permission(Action.RESEARCH_PUBLIC.value, "*"),
        Permission(Action.SUBMIT_FEEDBACK.value, "*"),
    ],
    Role.GUEST.value: [
        Permission(Action.RESEARCH_PUBLIC.value, "*"),
        Permission(Action.VIEW_DOCUMENT.value, "public"),
    ],
}


class RBACManager:
    """Manages role-based access control for the system."""

    def __init__(self):
        self.roles: Dict[str, User] = {}
        self._load_default_roles()

    def _load_default_roles(self):
        """Initialize default users."""
        # Admin user
        self.roles["admin"] = User(
            user_id="admin",
            username="admin",
            role=Role.ADMIN.value,
            department=None,
            allowed_document_categories=["*"],
        )
        # Demo employee
        self.roles["employee"] = User(
            user_id="employee",
            username="employee",
            role=Role.EMPLOYEE.value,
            department="engineering",
            allowed_document_categories=["engineering", "public"],
        )
        # Demo customer
        self.roles["customer"] = User(
            user_id="customer",
            username="customer",
            role=Role.CUSTOMER.value,
            department=None,
            allowed_document_categories=["public", "customer"],
        )

    def add_user(self, user: User):
        """Add or update a user."""
        self.roles[user.user_id] = user
        logger.info(f"[RBAC] User added/updated: {user.user_id} (role={user.role})")

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.roles.get(user_id)

    def get_permissions(self, user: User) -> List[Permission]:
        """Get all permissions for a user based on role."""
        role_perms = ROLE_PERMISSIONS.get(user.role, [])
        # Resolve template variables in resource strings
        resolved = []
        for perm in role_perms:
            resolved_perm = Permission(
                action=perm.action,
                resource=self._resolve_resource_template(perm.resource, user),
                conditions=dict(perm.conditions),
            )
            resolved.append(resolved_perm)
        return resolved

    def _resolve_resource_template(self, resource: str, user: User) -> str:
        """Resolve template variables like {department} in resource strings."""
        resolved = resource
        if "{department}" in resolved:
            resolved = resolved.replace("{department}", user.department or "none")
        if "{customer_id}" in resolved:
            resolved = resolved.replace("{customer_id}", user.user_id)
        return resolved

    def has_permission(self, user: User, action: str, resource: str = "*") -> bool:
        """
        Check if user has permission to perform action on resource.
        
        Args:
            user: The user to check
            action: The action to perform (e.g., "view_document")
            resource: The resource to access (e.g., "department:engineering", "public")
        
        Returns:
            True if permitted, False otherwise
        """
        if user.role == Role.ADMIN.value:
            return True
        
        permissions = self.get_permissions(user)
        
        for perm in permissions:
            if perm.action == action:
                # Check if resource matches
                if self._resource_matches(perm.resource, resource):
                    return True
                # Check conditions
                if self._check_conditions(perm.conditions, user, resource):
                    return True
        
        return False

    def _resource_matches(self, permission_resource: str, requested_resource: str) -> bool:
        """Check if a permission resource pattern matches the requested resource."""
        if permission_resource == "*":
            return True
        
        # Split comma-separated resources
        allowed_resources = [r.strip() for r in permission_resource.split(",")]
        
        for allowed in allowed_resources:
            if allowed == "*":
                return True
            if allowed == requested_resource:
                return True
            # Prefix matching: "department:engineering" matches "department:engineering/report.pdf"
            if requested_resource.startswith(allowed + "/") or requested_resource.startswith(allowed + ":"):
                return True
            # Category matching
            if ":" in allowed and requested_resource.startswith(allowed.split(":")[0] + ":"):
                return True
        
        return False

    def _check_conditions(self, conditions: Dict, user: User, resource: str) -> bool:
        """Check additional conditions for permission."""
        # "own" condition: user can only access their own resources
        if conditions.get("own") and not resource.startswith(f"user:{user.user_id}"):
            return False
        
        # Department condition
        if "department" in conditions:
            if user.department != conditions["department"]:
                return False
        
        return True

    def filter_documents(self, user: User, documents: List[Dict]) -> List[Dict]:
        """
        Filter documents based on user permissions.
        Returns only documents the user is allowed to view.
        """
        allowed = []
        for doc in documents:
            doc_category = doc.get("category", "public")
            doc_resource = f"category:{doc_category}"
            
            if self.has_permission(user, Action.VIEW_DOCUMENT.value, doc_resource):
                allowed.append(doc)
            elif self.has_permission(user, Action.VIEW_DOCUMENT.value, "public"):
                if doc_category == "public":
                    allowed.append(doc)
        
        return allowed

    def filter_memory_chunks(self, user: User, chunks: List[Dict]) -> List[Dict]:
        """
        Filter RAG memory chunks based on user permissions.
        Each chunk should have metadata with 'allowed_roles' or 'department'.
        """
        allowed = []
        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            allowed_roles = metadata.get("allowed_roles", ["*"])
            department = metadata.get("department")
            
            # Check role-based access
            role_allowed = "*" in allowed_roles or user.role in allowed_roles
            
            # Check department access
            dept_allowed = True
            if department:
                dept_allowed = (user.department == department) or (user.role == Role.ADMIN.value)
            
            if role_allowed and dept_allowed:
                allowed.append(chunk)
        
        return allowed

    def get_accessible_agents(self, user: User) -> List[str]:
        """Get list of agents the user can invoke."""
        if user is None:
            return ["supervisor", "research_agent"]  # Default for anonymous users
        
        if user.role == Role.ADMIN.value:
            return ["planner", "supervisor", "research_agent", "coder_agent", "validator", "reflection", "approval"]
        
        agents = ["supervisor", "reflection"]
        if self.has_permission(user, Action.RESEARCH_PUBLIC.value):
            agents.append("research_agent")
        if self.has_permission(user, Action.RESEARCH_PRIVATE.value):
            agents.append("research_agent")
        if self.has_permission(user, Action.EXECUTE_CODE.value):
            agents.append("coder_agent")
        
        return agents

    def can_approve(self, user: User, action_context: Dict) -> bool:
        """Check if user can approve a given action."""
        return self.has_permission(user, Action.APPROVE_ACTION.value, action_context.get("resource", "*"))

    def log_access(self, user_id: str, action: str, resource: str, granted: bool):
        """Log access attempt for audit."""
        logger.info(f"[RBAC] Access {'granted' if granted else 'denied'}: user={user_id}, action={action}, resource={resource}")


# Global RBAC manager instance
_rbac_manager: Optional[RBACManager] = None


def get_rbac_manager() -> RBACManager:
    """Get or create the global RBAC manager."""
    global _rbac_manager
    if _rbac_manager is None:
        _rbac_manager = RBACManager()
    return _rbac_manager


def get_current_user(user_id: str) -> Optional[User]:
    """Convenience function to get current user."""
    manager = get_rbac_manager()
    return manager.get_user(user_id)


def check_permission(user_id: str, action: str, resource: str = "*") -> bool:
    """Convenience function to check permission."""
    manager = get_rbac_manager()
    user = manager.get_user(user_id)
    if not user:
        return False
    return manager.has_permission(user, action, resource)


def filter_documents_for_user(user_id: str, documents: List[Dict]) -> List[Dict]:
    """Convenience function to filter documents for a user."""
    manager = get_rbac_manager()
    user = manager.get_user(user_id)
    if not user:
        return []
    return manager.filter_documents(user, documents)


def filter_memory_for_user(user_id: str, chunks: List[Dict]) -> List[Dict]:
    """Convenience function to filter memory chunks for a user."""
    manager = get_rbac_manager()
    user = manager.get_user(user_id)
    if not user:
        return []
    return manager.filter_memory_chunks(user, chunks)
