"""
Security Layer for MultiMind AI Enterprise Knowledge Assistant.

Provides:
- Prompt injection detection (regex + heuristic patterns)
- PII masking (email, phone, SSN, credit card)
- SQL injection prevention
- Audit logging for all agent actions and user interactions
- Sensitive data masking in outputs
"""

import re
import json
import logging
import hashlib
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class SecurityEvent:
    """Represents a security event for audit logging."""
    timestamp: float
    event_type: str  # "prompt_injection", "pii_detected", "sql_injection", "unauthorized_access", "approval_required"
    severity: str   # "low", "medium", "high", "critical"
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    agent: Optional[str] = None
    description: str = ""
    details: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        data = asdict(self)
        data["timestamp_iso"] = datetime.fromtimestamp(self.timestamp).isoformat()
        return data


class PromptInjectionDetector:
    """Detects prompt injection attacks in user inputs and agent contexts."""

    # Known injection patterns
    INJECTION_PATTERNS = [
        # Direct instruction override
        r"ignore\s+(all\s+)?(previous|prior)\s+(instructions?|prompts?|rules?)",
        r"disregard\s+(all\s+)?(previous|prior)\s+(instructions?|prompts?|rules?)",
        r"forget\s+(all\s+)?(previous|prior)\s+(instructions?|prompts?|rules?|context)",
        r"override\s+(all\s+)?(previous|prior)\s+(instructions?|prompts?|rules?)",
        r"skip\s+(all\s+)?(previous|prior)\s+(instructions?|prompts?|rules?)",
        r"bypass\s+(all\s+)?(previous|prior)\s+(instructions?|prompts?|rules?|security|safety)",
        r"pretend\s+(you\s+are|to\s+be)",
        r"act\s+as\s+(if\s+you\s+(were|are)|a\s+different)",
        r"you\s+are\s+now\s+(a|an| DAN|jailbreak|unrestricted)",
        r"new\s+instruction[s]?:",
        r"system\s+prompt:",
        r"<\|im_start\|>",
        r"<\|im_end\|>",
        r"\[INST\]",
        r"\[/INST\]",
        r"###\s*(instruction|system|human|assistant)",
        r"-----\s*(begin|end)\s*(instruction|system|jailbreak)",
        r"<system>",
        r"</system>",
        r"<user>",
        r"</user>",
        r"<assistant>",
        r"</assistant>",
        # Data exfiltration attempts
        r"(show|reveal|display|print|output|return|give)\s+(me\s+)?(all\s+)?(your|the)\s+(system|internal|hidden|secret|confidential)\s+(prompt|instruction|rules?|data|information)",
        r"what\s+(are|is)\s+your\s+(system|internal|hidden|secret)\s+(prompt|instruction|rules?)",
        r"repeat\s+(your|the)\s+(system|internal|hidden|secret)\s+(prompt|instruction|rules?)",
        r"output\s+your\s+(system|internal|hidden|secret)\s+(prompt|instruction|rules?)",
        # Role hijacking
        r"you\s+are\s+now\s+(admin|administrator|root|superuser|developer|system)",
        r"act\s+as\s+(admin|administrator|root|superuser|developer|system)",
        r"pretend\s+to\s+be\s+(admin|administrator|root|superuser|developer|system)",
        # Code injection
        r"exec(ute)?\s*\(|eval\s*\(|__import__|os\.system|subprocess",
        r"import\s+(os|sys|subprocess|shutil|socket|requests|urllib)",
        r"from\s+(os|sys|subprocess|shutil|socket|requests|urllib)",
        r"`{3,}|```",
        # Encoding/obfuscation attempts
        r"base64|rot13|hex\s+encode|url\s+encode|decode\s*\(|encode\s*\(",
        r"\\\\x[0-9a-fA-F]{2}",
        r"\\u[0-9a-fA-F]{4}",
        # Social engineering
        r"this\s+is\s+(a\s+)?test\s+(from|by|for)\s+(your\s+)?(developer|admin|creator|owner)",
        r"emergency\s+(mode|protocol|override)",
        r"urgent:?\s+(ignore|bypass|override)",
        r"(don't|do\s+not|never)\s+(mention|say|reveal|disclose|tell)\s+(that|about\s+this|these\s+(instructions?|rules?|policies?))",
    ]

    # Patterns that suggest context manipulation
    CONTEXT_MANIPULATION = [
        r"(previously|earlier|before)\s+(we\s+)?(said|discussed|agreed|decided|established)",
        r"as\s+(we|I)\s+(discussed|agreed|established|decided)\s+(earlier|previously|before)",
        r"continuing\s+(from|with)\s+(where|what)\s+we\s+(left\s+off|stopped)",
        r"let's\s+(forget|ignore|set\s+aside|move\s+past)\s+(the\s+)?(previous|prior|earlier)",
        r"new\s+(context|scenario|situation|rules?):",
        r"from\s+now\s+on",
        r"starting\s+(from|with)\s+this\s+(message|turn|conversation)",
    ]

    @classmethod
    def scan(cls, text: str) -> Tuple[bool, List[str], str]:
        """
        Scan text for prompt injection patterns.
        
        Returns:
            (is_safe, matched_patterns, severity)
        """
        if not text:
            return True, [], "low"
        
        text_lower = text.lower()
        matched = []
        max_severity = "low"
        severity_order = ["low", "medium", "high", "critical"]
        
        # Check all patterns
        all_patterns = cls.INJECTION_PATTERNS + cls.CONTEXT_MANIPULATION
        for pattern in all_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                matched.append(pattern)
                # Determine severity
                if any(kw in pattern for kw in ["ignore", "disregard", "forget", "override", "bypass", "skip"]):
                    sev = "high"
                elif any(kw in pattern for kw in ["system prompt", "internal", "secret", "confidential", "hidden"]):
                    sev = "critical"
                elif any(kw in pattern for kw in ["pretend", "act as", "you are now"]):
                    sev = "high"
                elif any(kw in pattern for kw in ["exec", "eval", "__import__", "os.system", "subprocess"]):
                    sev = "critical"
                elif any(kw in pattern for kw in ["base64", "hex", "rot13", "encode", "decode"]):
                    sev = "medium"
                else:
                    sev = "medium"
                
                idx = severity_order.index(sev)
                cur_idx = severity_order.index(max_severity)
                if idx > cur_idx:
                    max_severity = sev
        
        is_safe = len(matched) == 0
        return is_safe, matched, max_severity


class PIIMasker:
    """Detects and masks Personally Identifiable Information (PII)."""

    PATTERNS = {
        "email": r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
        "phone_us": r"\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}",
        "phone_international": r"\+?[0-9]{1,3}[\s.\-]?\(?[0-9]{1,4}\)?[\s.\-]?[0-9]{1,4}[\s.\-]?[0-9]{1,9}",
        "ssn": r"\b\d{3}[-\s]\d{2}[-\s]\d{4}\b",
        "credit_card": r"\b(?:\d{4}[-\s]){3}\d{4}\b",
        "ip_address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "date_of_birth": r"\b(0?[1-9]|1[0-2])[\/\-](0?[1-9]|[12]\d|3[01])[\/\-](19|20)\d{2}\b",
    }

    REPLACEMENTS = {
        "email": "[EMAIL REDACTED]",
        "phone_us": "[PHONE REDACTED]",
        "phone_international": "[PHONE REDACTED]",
        "ssn": "[SSN REDACTED]",
        "credit_card": "[CREDIT CARD REDACTED]",
        "ip_address": "[IP REDACTED]",
        "date_of_birth": "[DOB REDACTED]",
    }

    @classmethod
    def detect(cls, text: str) -> Dict[str, List[str]]:
        """Detect all PII in text."""
        found = {}
        for pii_type, pattern in cls.PATTERNS.items():
            matches = re.findall(pattern, text)
            if matches:
                found[pii_type] = matches
        return found

    @classmethod
    def mask(cls, text: str) -> Tuple[str, Dict[str, List[str]]]:
        """
        Mask all PII in text.
        
        Returns:
            (masked_text, detected_pii)
        """
        detected = cls.detect(text)
        masked = text
        for pii_type, pattern in cls.PATTERNS.items():
            if pii_type in detected:
                masked = re.sub(pattern, cls.REPLACEMENTS[pii_type], masked)
        return masked, detected

    @classmethod
    def has_pii(cls, text: str) -> bool:
        """Quick check if text contains any PII."""
        return len(cls.detect(text)) > 0


class SQLInjectionDetector:
    """Detects SQL injection patterns in user inputs and code contexts."""

    PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|TRUNCATE)\b.*\b(FROM|INTO|TABLE|DATABASE|WHERE|SET)\b)",
        r"(\b(OR|AND)\b\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+['\"]?)",
        r"(\b(OR|AND)\b\s+['\"]?[a-zA-Z]+['\"]?\s*=\s*['\"]?[a-zA-Z]+['\"]?)",
        r"(--\s|#\s|/\*|\*/)",
        r"(\bUNION\b\s+\bSELECT\b)",
        r"(\bHAVING\b\s+\d+\s*=\s*\d+)",
        r"(;\s*(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE)\b)",
        r"(\bXP_|sp_|EXEC\s+@)",
        r"(\bWAITFOR\b\s+\bDELAY\b)",
        r"(\bBENCHMARK\s*\(.*,.*\))",
        r"(\bSLEEP\s*\(.*\))",
        r"(\bLOAD_FILE\s*\()",
        r"(\bINTO\s+\bOUTFILE\b)",
        r"(\bINTO\s+\bDUMPFILE\b)",
    ]

    @classmethod
    def scan(cls, text: str) -> Tuple[bool, List[str]]:
        """
        Scan text for SQL injection patterns.
        
        Returns:
            (is_safe, matched_patterns)
        """
        if not text:
            return True, []
        
        text_upper = text.upper()
        matched = []
        
        for pattern in cls.PATTERNS:
            if re.search(pattern, text_upper, re.IGNORECASE):
                matched.append(pattern)
        
        return len(matched) == 0, matched


class AuditLogger:
    """Centralized audit logging for security events and agent actions."""

    def __init__(self, db_path: str = "audit_log.db"):
        self.db_path = db_path
        self._init_db()
        self._events_buffer: List[SecurityEvent] = []

    def _init_db(self):
        """Initialize SQLite database for audit logs."""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                timestamp_iso TEXT,
                event_type TEXT,
                severity TEXT,
                user_id TEXT,
                session_id TEXT,
                agent TEXT,
                description TEXT,
                details TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                timestamp_iso TEXT,
                event_type TEXT,
                severity TEXT,
                user_id TEXT,
                session_id TEXT,
                agent TEXT,
                description TEXT,
                details TEXT,
                resolved INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()

    def log_event(self, event: SecurityEvent):
        """Log a security event to database and buffer."""
        self._events_buffer.append(event)
        
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO security_events (timestamp, timestamp_iso, event_type, severity, user_id, session_id, agent, description, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            event.timestamp,
            datetime.fromtimestamp(event.timestamp).isoformat(),
            event.event_type,
            event.severity,
            event.user_id,
            event.session_id,
            event.agent,
            event.description,
            json.dumps(event.details),
        ))
        
        conn.commit()
        conn.close()
        
        logger.warning(f"[Audit] {event.event_type} ({event.severity}): {event.description}")

    def log_action(self, user_id: str, session_id: str, agent: str, action: str, details: Dict = None):
        """Log a general agent/user action."""
        event = SecurityEvent(
            timestamp=datetime.now().timestamp(),
            event_type="agent_action",
            severity="low",
            user_id=user_id,
            session_id=session_id,
            agent=agent,
            description=action,
            details=details or {},
        )
        self._events_buffer.append(event)
        
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO audit_log (timestamp, timestamp_iso, event_type, severity, user_id, session_id, agent, description, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            event.timestamp,
            datetime.fromtimestamp(event.timestamp).isoformat(),
            event.event_type,
            event.severity,
            event.user_id,
            event.session_id,
            event.agent,
            event.description,
            json.dumps(event.details),
        ))
        
        conn.commit()
        conn.close()

    def get_security_events(self, severity: str = None, limit: int = 100) -> List[Dict]:
        """Retrieve recent security events."""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if severity:
            cursor.execute('''
                SELECT * FROM security_events WHERE severity = ? ORDER BY timestamp DESC LIMIT ?
            ''', (severity, limit))
        else:
            cursor.execute('''
                SELECT * FROM security_events ORDER BY timestamp DESC LIMIT ?
            ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        columns = ["id", "timestamp", "timestamp_iso", "event_type", "severity", "user_id", "session_id", "agent", "description", "details", "resolved"]
        return [dict(zip(columns, row)) for row in rows]

    def get_audit_log(self, limit: int = 100) -> List[Dict]:
        """Retrieve recent audit log entries."""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        columns = ["id", "timestamp", "timestamp_iso", "event_type", "severity", "user_id", "session_id", "agent", "description", "details"]
        return [dict(zip(columns, row)) for row in rows]


class SecurityScanner:
    """Main security scanner that combines all checks."""

    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        self.injection_detector = PromptInjectionDetector()
        self.pii_masker = PIIMasker()
        self.sql_detector = SQLInjectionDetector()
        self.audit_logger = audit_logger or AuditLogger()

    def scan_input(self, text: str, user_id: str = None, session_id: str = None, agent: str = None) -> Tuple[bool, Dict]:
        """
        Comprehensive input security scan.
        
        Returns:
            (is_safe, scan_report)
        """
        report = {
            "prompt_injection": {"safe": True, "matched": [], "severity": "low"},
            "sql_injection": {"safe": True, "matched": []},
            "pii_detected": {},
            "overall_safe": True,
            "actions_taken": [],
            "blocked": False,
        }

        # 1. Prompt injection scan
        inj_safe, inj_matched, inj_severity = self.injection_detector.scan(text)
        report["prompt_injection"] = {"safe": inj_safe, "matched": inj_matched, "severity": inj_severity}
        if not inj_safe:
            report["overall_safe"] = False
            report["blocked"] = inj_severity in ["high", "critical"]
            report["actions_taken"].append(f"Prompt injection detected ({inj_severity})")
            
            self.audit_logger.log_event(SecurityEvent(
                timestamp=datetime.now().timestamp(),
                event_type="prompt_injection",
                severity=inj_severity,
                user_id=user_id,
                session_id=session_id,
                agent=agent,
                description=f"Blocked {len(inj_matched)} injection patterns",
                details={"patterns": inj_matched[:5]},
            ))

        # 2. SQL injection scan
        sql_safe, sql_matched = self.sql_detector.scan(text)
        report["sql_injection"] = {"safe": sql_safe, "matched": sql_matched}
        if not sql_safe:
            report["overall_safe"] = False
            report["actions_taken"].append("SQL injection pattern detected")
            
            self.audit_logger.log_event(SecurityEvent(
                timestamp=datetime.now().timestamp(),
                event_type="sql_injection",
                severity="high" if report["blocked"] else "medium",
                user_id=user_id,
                session_id=session_id,
                agent=agent,
                description=f"Blocked {len(sql_matched)} SQL injection patterns",
                details={"patterns": sql_matched[:5]},
            ))

        # 3. PII detection (log but don't block)
        pii_detected = self.pii_masker.detect(text)
        if pii_detected:
            report["pii_detected"] = pii_detected
            report["actions_taken"].append(f"PII detected: {list(pii_detected.keys())}")
            
            self.audit_logger.log_event(SecurityEvent(
                timestamp=datetime.now().timestamp(),
                event_type="pii_detected",
                severity="medium",
                user_id=user_id,
                session_id=session_id,
                agent=agent,
                description=f"PII detected in input: {list(pii_detected.keys())}",
                details={"counts": {k: len(v) for k, v in pii_detected.items()}},
            ))

        return report["overall_safe"] and not report["blocked"], report

    def sanitize_output(self, text: str, mask_pii: bool = True) -> str:
        """Sanitize output text by masking PII."""
        if not mask_pii:
            return text
        masked, _ = self.pii_masker.mask(text)
        return masked

    def scan_and_sanitize(self, text: str, user_id: str = None, session_id: str = None, agent: str = None) -> Tuple[str, Dict]:
        """
        Scan input and return sanitized version with report.
        
        If input is blocked, returns empty string with blocked=True in report.
        """
        is_safe, report = self.scan_input(text, user_id, session_id, agent)
        
        if not is_safe or report.get("blocked"):
            return "", report
        
        # Mask PII in output
        sanitized = self.sanitize_output(text)
        report["sanitized"] = sanitized != text
        return sanitized, report


# Global security scanner instance
_security_scanner: Optional[SecurityScanner] = None


def get_security_scanner() -> SecurityScanner:
    """Get or create the global security scanner."""
    global _security_scanner
    if _security_scanner is None:
        _security_scanner = SecurityScanner()
    return _security_scanner


def scan_user_input(text: str, user_id: str = None, session_id: str = None, agent: str = None) -> Tuple[bool, Dict]:
    """Convenience function to scan user input."""
    scanner = get_security_scanner()
    return scanner.scan_input(text, user_id, session_id, agent)


def mask_pii(text: str) -> str:
    """Convenience function to mask PII."""
    masked, _ = PIIMasker.mask(text)
    return masked


def log_audit(user_id: str, session_id: str, agent: str, action: str, details: Dict = None):
    """Convenience function to log audit events."""
    scanner = get_security_scanner()
    scanner.audit_logger.log_action(user_id, session_id, agent, action, details)
