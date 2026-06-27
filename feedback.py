"""
User Feedback Module for MultiMind AI Enterprise Knowledge Assistant.

Provides:
- Thumbs up/down feedback collection
- Feedback storage in SQLite
- Trust score adjustment based on feedback
- Retraining signal aggregation
- Feedback-driven policy improvement
"""

import sqlite3
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class FeedbackEntry:
    """Represents a user feedback entry."""
    feedback_id: str
    session_id: str
    user_id: str
    query: str
    agent: str
    output: str
    feedback_type: str  # "thumbs_up", "thumbs_down", "rating"
    rating: Optional[int] = None  # 1-5 scale
    comment: Optional[str] = None
    timestamp: float = field(default_factory=datetime.now().timestamp)
    processed: bool = False
    trust_adjustment: float = 0.0

    def to_dict(self) -> Dict:
        data = asdict(self)
        data["timestamp_iso"] = datetime.fromtimestamp(self.timestamp).isoformat()
        return data


class FeedbackStore:
    """Stores and manages user feedback."""

    def __init__(self, db_path: str = "feedback.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database for feedback."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                feedback_id TEXT PRIMARY KEY,
                session_id TEXT,
                user_id TEXT,
                query TEXT,
                agent TEXT,
                output TEXT,
                feedback_type TEXT,
                rating INTEGER,
                comment TEXT,
                timestamp REAL,
                timestamp_iso TEXT,
                processed INTEGER DEFAULT 0,
                trust_adjustment REAL DEFAULT 0.0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback_aggregates (
                agent TEXT PRIMARY KEY,
                total_feedback INTEGER DEFAULT 0,
                positive_count INTEGER DEFAULT 0,
                negative_count INTEGER DEFAULT 0,
                average_rating REAL DEFAULT 0.0,
                last_updated TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trust_adjustments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feedback_id TEXT,
                agent TEXT,
                content_hash TEXT,
                adjustment REAL,
                reason TEXT,
                timestamp TEXT
            )
        ''')
        
        conn.commit()
        conn.close()

    def add_feedback(
        self,
        session_id: str,
        user_id: str,
        query: str,
        agent: str,
        output: str,
        feedback_type: str,
        rating: int = None,
        comment: str = None,
    ) -> FeedbackEntry:
        """Add a new feedback entry."""
        feedback_id = f"fb_{int(datetime.now().timestamp() * 1000)}_{hash(query + user_id) % 10000:04d}"
        
        entry = FeedbackEntry(
            feedback_id=feedback_id,
            session_id=session_id,
            user_id=user_id,
            query=query,
            agent=agent,
            output=output,
            feedback_type=feedback_type,
            rating=rating,
            comment=comment,
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO feedback (feedback_id, session_id, user_id, query, agent, output, feedback_type, rating, comment, timestamp, timestamp_iso)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            entry.feedback_id,
            entry.session_id,
            entry.user_id,
            entry.query,
            entry.agent,
            entry.output,
            entry.feedback_type,
            entry.rating,
            entry.comment,
            entry.timestamp,
            datetime.fromtimestamp(entry.timestamp).isoformat(),
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"[Feedback] Added feedback: {feedback_id} (type={feedback_type}, agent={agent})")
        
        # Update aggregates
        self._update_aggregates(agent, feedback_type, rating)
        
        return entry

    def get_feedback(self, agent: str = None, user_id: str = None, limit: int = 100) -> List[Dict]:
        """Get feedback entries, optionally filtered."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM feedback WHERE 1=1"
        params = []
        
        if agent:
            query += " AND agent = ?"
            params.append(agent)
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        columns = ["feedback_id", "session_id", "user_id", "query", "agent", "output", 
                   "feedback_type", "rating", "comment", "timestamp", "timestamp_iso", 
                   "processed", "trust_adjustment"]
        return [dict(zip(columns, row)) for row in rows]

    def get_agent_stats(self, agent: str) -> Dict:
        """Get aggregate stats for an agent."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT total_feedback, positive_count, negative_count, average_rating, last_updated
            FROM feedback_aggregates WHERE agent = ?
        ''', (agent,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "agent": agent,
                "total_feedback": row[0],
                "positive_count": row[1],
                "negative_count": row[2],
                "average_rating": row[3],
                "last_updated": row[4],
            }
        return {"agent": agent, "total_feedback": 0, "positive_count": 0, "negative_count": 0, "average_rating": 0.0}

    def _update_aggregates(self, agent: str, feedback_type: str, rating: Optional[int]):
        """Update aggregate stats for an agent."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current stats
        cursor.execute('SELECT * FROM feedback_aggregates WHERE agent = ?', (agent,))
        row = cursor.fetchone()
        
        if row:
            total = row[1] + 1
            positive = row[2] + (1 if feedback_type == "thumbs_up" else 0)
            negative = row[3] + (1 if feedback_type == "thumbs_down" else 0)
            ratings = self._get_all_ratings(agent)
            ratings.append(rating) if rating else None
            avg_rating = sum(ratings) / len(ratings) if ratings else 0.0
            
            cursor.execute('''
                UPDATE feedback_aggregates 
                SET total_feedback=?, positive_count=?, negative_count=?, average_rating=?, last_updated=?
                WHERE agent=?
            ''', (total, positive, negative, avg_rating, datetime.now().isoformat(), agent))
        else:
            positive = 1 if feedback_type == "thumbs_up" else 0
            negative = 1 if feedback_type == "thumbs_down" else 0
            avg_rating = rating if rating else 0.0
            
            cursor.execute('''
                INSERT INTO feedback_aggregates (agent, total_feedback, positive_count, negative_count, average_rating, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (agent, 1, positive, negative, avg_rating, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()

    def _get_all_ratings(self, agent: str) -> List[int]:
        """Get all ratings for an agent."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT rating FROM feedback WHERE agent = ? AND rating IS NOT NULL', (agent,))
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]

    def adjust_trust_score(
        self,
        feedback_id: str,
        content_hash: str,
        agent: str,
        adjustment: float,
        reason: str = "",
    ):
        """Record a trust score adjustment based on feedback."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO trust_adjustments (feedback_id, agent, content_hash, adjustment, reason, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            feedback_id,
            agent,
            content_hash,
            adjustment,
            reason,
            datetime.now().isoformat(),
        ))
        
        # Mark feedback as processed
        cursor.execute('UPDATE feedback SET processed=1, trust_adjustment=? WHERE feedback_id=?', (adjustment, feedback_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"[Feedback] Trust score adjusted for {feedback_id}: {adjustment:+.2f} ({reason})")

    def get_retraining_signals(self, min_negative_count: int = 5) -> List[Dict]:
        """
        Get retraining signals: agents with high negative feedback.
        
        Returns:
            List of agents that need attention
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT agent, negative_count, total_feedback, average_rating
            FROM feedback_aggregates
            WHERE negative_count >= ? AND total_feedback >= 10
            ORDER BY (negative_count * 1.0 / total_feedback) DESC
        ''', (min_negative_count,))
        
        rows = cursor.fetchall()
        conn.close()
        
        signals = []
        for row in rows:
            negative_ratio = row[1] / row[2] if row[2] > 0 else 0
            signals.append({
                "agent": row[0],
                "negative_count": row[1],
                "total_feedback": row[2],
                "negative_ratio": negative_ratio,
                "average_rating": row[3],
                "recommendation": "Review prompt/training data" if negative_ratio > 0.3 else "Monitor closely",
            })
        
        return signals

    def get_feedback_trends(self, days: int = 7) -> Dict:
        """Get feedback trends over the last N days."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff = (datetime.now().timestamp() - (days * 24 * 3600))
        
        cursor.execute('''
            SELECT DATE(timestamp_iso) as date, feedback_type, COUNT(*) as count
            FROM feedback
            WHERE timestamp >= ?
            GROUP BY DATE(timestamp_iso), feedback_type
            ORDER BY date DESC
        ''', (cutoff,))
        
        rows = cursor.fetchall()
        conn.close()
        
        trends = {}
        for row in rows:
            date, ftype, count = row
            if date not in trends:
                trends[date] = {}
            trends[date][ftype] = count
        
        return trends


# Global feedback store instance
_feedback_store: Optional[FeedbackStore] = None


def get_feedback_store() -> FeedbackStore:
    """Get or create the global feedback store."""
    global _feedback_store
    if _feedback_store is None:
        _feedback_store = FeedbackStore()
    return _feedback_store


def submit_feedback(
    session_id: str,
    user_id: str,
    query: str,
    agent: str,
    output: str,
    feedback_type: str,
    rating: int = None,
    comment: str = None,
) -> FeedbackEntry:
    """Convenience function to submit feedback."""
    store = get_feedback_store()
    return store.add_feedback(session_id, user_id, query, agent, output, feedback_type, rating, comment)


def get_feedback_stats(agent: str = None) -> Dict:
    """Convenience function to get feedback stats."""
    store = get_feedback_store()
    if agent:
        return store.get_agent_stats(agent)
    return {}


def get_retraining_signals() -> List[Dict]:
    """Convenience function to get retraining signals."""
    store = get_feedback_store()
    return store.get_retraining_signals()
