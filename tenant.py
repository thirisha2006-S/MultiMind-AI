"""
Multi-Tenant Architecture for MultiMind AI.
Isolates knowledge, users, and operations between organizations.
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class Tenant:
    """Represents an organization/tenant in the system."""
    tenant_id: str
    name: str
    created_at: float
    config: Dict[str, Any] = field(default_factory=dict)


class TenantContext:
    """
    Provides tenant-aware context for all operations.
    
    Tenant isolation:
    - Documents stored separately per tenant
    - FAISS indices isolated per tenant
    - Users scoped to tenants
    - Audits scoped to tenants
    """
    
    def __init__(self):
        self._current_tenant: Optional[Tenant] = None
        self._tenants: Dict[str, Tenant] = {}
    
    def set_tenant(self, tenant_id: str) -> Tenant:
        """
        Set the current tenant context.
        Creates tenant if it doesn't exist.
        """
        import time
        if tenant_id not in self._tenants:
            self._tenants[tenant_id] = Tenant(
                tenant_id=tenant_id,
                name=tenant_id.title(),
                created_at=time.time()
            )
            logger.info(f"[Tenant] Created new tenant: {tenant_id}")
        
        self._current_tenant = self._tenants[tenant_id]
        return self._current_tenant
    
    def get_tenant_id(self) -> Optional[str]:
        """Get the current tenant ID."""
        return self._current_tenant.tenant_id if self._current_tenant else None
    
    def get_tenant(self) -> Optional[Tenant]:
        """Get the current tenant object."""
        return self._current_tenant
    
    def clear_tenant(self):
        """Clear current tenant context."""
        self._current_tenant = None
    
    def get_tenant_config(self, key: str, default: Any = None) -> Any:
        """Get tenant-specific configuration."""
        if not self._current_tenant:
            return default
        return self._current_tenant.config.get(key, default)


# Global tenant context
_tenant_context: Optional[TenantContext] = None


def get_tenant_context() -> TenantContext:
    """Get or create the global tenant context."""
    global _tenant_context
    if _tenant_context is None:
        _tenant_context = TenantContext()
    return _tenant_context


def set_tenant(tenant_id: str) -> Tenant:
    """Convenience function to set tenant."""
    return get_tenant_context().set_tenant(tenant_id)


def get_tenant_id() -> Optional[str]:
    """Convenience function to get current tenant ID."""
    return get_tenant_context().get_tenant_id()


def with_tenant(tenant_id: str):
    """
    Context manager for tenant operations.
    
    Usage:
        with with_tenant("company-a"):
            result = run_task("What is our policy?")
    """
    import contextlib
    
    @contextlib.contextmanager
    def tenant_context():
        ctx = get_tenant_context()
        old_tenant = ctx.get_tenant_id()
        ctx.set_tenant(tenant_id)
        try:
            yield
        finally:
            if old_tenant:
                ctx.set_tenant(old_tenant)
            else:
                ctx.clear_tenant()
    
    return tenant_context()


# Tenant-aware memory key prefix
def tenant_memory_key(base_key: str) -> str:
    """Generate tenant-prefixed key for storage isolation."""
    tenant_id = get_tenant_id()
    if tenant_id:
        return f"tenant:{tenant_id}:{base_key}"
    return base_key


# Tenant filtering for RAG retrieval
def filter_by_tenant(results: List[Dict]) -> List[Dict]:
    """Filter RAG results to only include current tenant's knowledge."""
    tenant_id = get_tenant_id()
    if not tenant_id:
        return results
    
    # Add tenant filtering to results
    for r in results:
        r["tenant_id"] = r.get("tenant_id", tenant_id)
    
    return [r for r in results if r.get("tenant_id") == tenant_id or r.get("tenant_id") is None]


def add_tenant_metadata(metadata: Dict) -> Dict:
    """Add tenant metadata to any knowledge chunk."""
    tenant_id = get_tenant_id()
    if tenant_id:
        metadata["tenant_id"] = tenant_id
        metadata["_tenant_id"] = tenant_id
    return metadata