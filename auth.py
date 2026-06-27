"""
Authentication Module for MultiMind AI Enterprise Knowledge Assistant.

Provides:
- Session-based authentication for Streamlit dashboard
- User credential management
- Role-aware session state
- Password hashing (SHA-256 with salt for demo; BCrypt in production)
"""

import hashlib
import secrets
import logging
import json
from typing import Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from rbac import get_rbac_manager, User, Role

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """Represents an authenticated session."""
    session_id: str
    user_id: str
    username: str
    role: str
    department: Optional[str]
    created_at: datetime
    expires_at: datetime
    is_active: bool = True

    def is_valid(self) -> bool:
        """Check if session is still valid."""
        return self.is_active and datetime.now() < self.expires_at

    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "username": self.username,
            "role": self.role,
            "department": self.department,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "is_active": self.is_active,
        }


class AuthManager:
    """Manages authentication, sessions, and user credentials."""

    def __init__(self, session_timeout_minutes: int = 480):  # 8 hours default
        self.sessions: Dict[str, Session] = {}
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self._demo_credentials = self._init_demo_credentials()
        self.rbac = get_rbac_manager()

    def _init_demo_credentials(self) -> Dict[str, str]:
        """Initialize demo user credentials (username -> hashed_password)."""
        # In production, these would be in a database with proper hashing (bcrypt/argon2)
        # Passwords: admin123, emp123, cust123
        return {
            "admin": self._hash_password("admin123"),
            "employee": self._hash_password("emp123"),
            "customer": self._hash_password("cust123"),
            "guest": self._hash_password("guest123"),
        }

    def _hash_password(self, password: str, salt: str = None) -> str:
        """Hash password with SHA-256 and salt."""
        if salt is None:
            salt = secrets.token_hex(16)
        hashed = hashlib.sha256((salt + password).encode()).hexdigest()
        return f"{salt}:{hashed}"

    def _verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify password against stored hash."""
        try:
            salt, hashed = stored_hash.split(":")
            return hashlib.sha256((salt + password).encode()).hexdigest() == hashed
        except ValueError:
            return False

    def authenticate(self, username: str, password: str) -> Optional[Session]:
        """
        Authenticate user with username and password.
        
        Returns:
            Session if successful, None otherwise
        """
        if username not in self._demo_credentials:
            logger.warning(f"[Auth] Failed login attempt for unknown user: {username}")
            return None
        
        stored_hash = self._demo_credentials[username]
        if not self._verify_password(password, stored_hash):
            logger.warning(f"[Auth] Failed login attempt for user: {username} (wrong password)")
            return None
        
        # Get user from RBAC
        user = self.rbac.get_user(username)
        if not user:
            # Create user from RBAC defaults
            role_map = {
                "admin": Role.ADMIN.value,
                "employee": Role.EMPLOYEE.value,
                "customer": Role.CUSTOMER.value,
                "guest": Role.GUEST.value,
            }
            user = User(
                user_id=username,
                username=username,
                role=role_map.get(username, Role.GUEST.value),
                department="engineering" if username == "employee" else None,
                allowed_document_categories=["*"] if username == "admin" else (
                    ["engineering", "public"] if username == "employee" else ["public", "customer"]
                ),
            )
        
        # Create session
        session_id = self._generate_session_id()
        now = datetime.now()
        session = Session(
            session_id=session_id,
            user_id=user.user_id,
            username=user.username,
            role=user.role,
            department=user.department,
            created_at=now,
            expires_at=now + self.session_timeout,
        )
        
        self.sessions[session_id] = session
        logger.info(f"[Auth] User authenticated: {username} (role={user.role})")
        return session

    def validate_session(self, session_id: str) -> Optional[Session]:
        """Validate an existing session."""
        session = self.sessions.get(session_id)
        if not session:
            return None
        if not session.is_valid():
            self.invalidate_session(session_id)
            return None
        return session

    def invalidate_session(self, session_id: str):
        """Invalidate a session."""
        if session_id in self.sessions:
            self.sessions[session_id].is_active = False
            del self.sessions[session_id]
            logger.info(f"[Auth] Session invalidated: {session_id}")

    def logout(self, session_id: str):
        """Logout user by invalidating session."""
        self.invalidate_session(session_id)

    def _generate_session_id(self) -> str:
        """Generate a secure session ID."""
        return secrets.token_urlsafe(32)

    def get_active_sessions(self) -> List[Dict]:
        """Get all active sessions (for admin dashboard)."""
        return [
            s.to_dict() for s in self.sessions.values() 
            if s.is_valid()
        ]

    def cleanup_expired_sessions(self):
        """Remove expired sessions."""
        expired = [sid for sid, s in self.sessions.items() if not s.is_valid()]
        for sid in expired:
            del self.sessions[sid]
        if expired:
            logger.info(f"[Auth] Cleaned up {len(expired)} expired sessions")


# Global auth manager instance
_auth_manager: Optional[AuthManager] = None


def get_auth_manager() -> AuthManager:
    """Get or create the global auth manager."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager


def authenticate_user(username: str, password: str) -> Optional[Session]:
    """Convenience function to authenticate a user."""
    manager = get_auth_manager()
    return manager.authenticate(username, password)


def validate_session(session_id: str) -> Optional[Session]:
    """Convenience function to validate a session."""
    manager = get_auth_manager()
    return manager.validate_session(session_id)


def get_current_session(session_id: str) -> Optional[Dict]:
    """Convenience function to get current session as dict."""
    session = validate_session(session_id)
    return session.to_dict() if session else None


# Streamlit-specific helpers
def get_streamlit_session_state():
    """Get Streamlit session state with lazy import."""
    try:
        import streamlit as st
        return st.session_state
    except ImportError:
        return {}


def login_streamlit(username: str, password: str) -> bool:
    """Login helper for Streamlit dashboard."""
    manager = get_auth_manager()
    session = manager.authenticate(username, password)
    if session:
        st_state = get_streamlit_session_state()
        if hasattr(st_state, '__setitem__'):
            st_state["authenticated"] = True
            st_state["user"] = session.to_dict()
        return True
    return False


def logout_streamlit():
    """Logout helper for Streamlit dashboard."""
    manager = get_auth_manager()
    st_state = get_streamlit_session_state()
    session_id = st_state.get("user", {}).get("session_id")
    if session_id:
        manager.invalidate_session(session_id)
    if hasattr(st_state, '__setitem__'):
        st_state["authenticated"] = False
        st_state["user"] = None


def is_authenticated() -> bool:
    """Check if current Streamlit session is authenticated."""
    st_state = get_streamlit_session_state()
    if hasattr(st_state, 'get'):
        return st_state.get("authenticated", False)
    return False


def get_current_user() -> Optional[Dict]:
    """Get current authenticated user from Streamlit session."""
    st_state = get_streamlit_session_state()
    if hasattr(st_state, 'get'):
        return st_state.get("user")
    return None
