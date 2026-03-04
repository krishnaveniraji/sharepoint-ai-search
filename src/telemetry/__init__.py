"""
Telemetry Logging for SharePoint AI Knowledge Assistant

Logs every search query, result, user action, and system event to a
local JSON-lines file for analytics and monitoring.

What gets logged:
    - Search queries (who searched, what, when, filters applied)
    - Search results (count, top scores, departments returned)
    - User sessions (login, role, duration)
    - Security events (access denied, confidential doc accessed)
    - Performance metrics (search latency, embedding generation time)

Storage:
    - JSON-lines format (.jsonl) — one JSON object per line
    - Easy to parse, append-only, no database needed
    - Located in /logs/ directory
    - Separate files: search_log.jsonl, security_log.jsonl, performance_log.jsonl
"""

import json
import os
import time
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

# ========================================
# LOG DIRECTORY SETUP
# ========================================

LOG_DIR = Path("logs")
SEARCH_LOG_FILE = LOG_DIR / "search_log.jsonl"
SECURITY_LOG_FILE = LOG_DIR / "security_log.jsonl"
PERFORMANCE_LOG_FILE = LOG_DIR / "performance_log.jsonl"


def _ensure_log_dir():
    """Create logs directory if it doesn't exist"""
    LOG_DIR.mkdir(exist_ok=True)


def _append_log(filepath: Path, data: dict):
    """Append a JSON line to a log file"""
    _ensure_log_dir()
    try:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, default=str) + "\n")
    except Exception as e:
        logger.error(f"Failed to write log to {filepath}: {e}")


def _read_logs(filepath: Path, limit: int = None) -> List[dict]:
    """Read log entries from a JSONL file"""
    if not filepath.exists():
        return []
    
    entries = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
    except Exception as e:
        logger.error(f"Failed to read log from {filepath}: {e}")
    
    if limit:
        return entries[-limit:]  # Return last N entries
    return entries


# ========================================
# SEARCH TELEMETRY
# ========================================

def log_search_query(
    query: str,
    user_email: str,
    user_role: str,
    departments_filter: List[str],
    security_filter: Optional[str],
    result_count: int,
    top_scores: List[float] = None,
    top_departments: List[str] = None,
    top_security_levels: List[str] = None,
    search_latency_ms: float = None,
    session_id: str = None
):
    """
    Log a search query and its results.
    
    Called after every search execution in app.py.
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "search_query",
        "session_id": session_id,
        
        # Query details
        "query": query,
        "query_length": len(query),
        "query_word_count": len(query.split()),
        
        # User context
        "user_email": user_email,
        "user_role": user_role,
        
        # Filters applied
        "departments_filter": departments_filter,
        "security_filter_applied": security_filter is not None,
        
        # Results
        "result_count": result_count,
        "has_results": result_count > 0,
        "top_scores": top_scores[:3] if top_scores else [],
        "top_departments": top_departments[:5] if top_departments else [],
        "top_security_levels": top_security_levels[:3] if top_security_levels else [],
        
        # Performance
        "search_latency_ms": search_latency_ms
    }
    
    _append_log(SEARCH_LOG_FILE, entry)


def log_no_results(
    query: str,
    user_email: str,
    user_role: str,
    departments_filter: List[str],
    reason: str = "no_match"
):
    """Log when a search returns zero results — useful for improving search quality"""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "no_results",
        "query": query,
        "user_email": user_email,
        "user_role": user_role,
        "departments_filter": departments_filter,
        "reason": reason  # "no_match", "access_denied", "filter_too_narrow"
    }
    
    _append_log(SEARCH_LOG_FILE, entry)


# ========================================
# SECURITY TELEMETRY
# ========================================

def log_security_event(
    event_type: str,
    user_email: str,
    user_role: str,
    details: Dict[str, Any] = None
):
    """
    Log security-related events.
    
    Event types:
        - user_login: User selected/logged in
        - access_filtered: Documents filtered out by RBAC
        - confidential_access: User accessed confidential document
        - department_restricted: User tried to access restricted department
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "user_email": user_email,
        "user_role": user_role,
        "details": details or {}
    }
    
    _append_log(SECURITY_LOG_FILE, entry)


def log_user_login(user_email: str, user_role: str, departments: List[str]):
    """Log user login/selection"""
    log_security_event(
        event_type="user_login",
        user_email=user_email,
        user_role=user_role,
        details={
            "departments": departments,
            "login_time": datetime.now(timezone.utc).isoformat()
        }
    )


def log_confidential_access(
    user_email: str,
    user_role: str,
    document_title: str,
    department: str
):
    """Log when a user accesses a confidential document"""
    log_security_event(
        event_type="confidential_access",
        user_email=user_email,
        user_role=user_role,
        details={
            "document_title": document_title,
            "department": department
        }
    )


# ========================================
# PERFORMANCE TELEMETRY
# ========================================

class SearchTimer:
    """Context manager for timing search operations"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.latency_ms = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, *args):
        self.end_time = time.perf_counter()
        self.latency_ms = (self.end_time - self.start_time) * 1000


def log_performance(
    operation: str,
    latency_ms: float,
    details: Dict[str, Any] = None
):
    """
    Log performance metrics.
    
    Operations: "search", "embedding_generation", "index_creation", "document_download"
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "performance",
        "operation": operation,
        "latency_ms": round(latency_ms, 2),
        "details": details or {}
    }
    
    _append_log(PERFORMANCE_LOG_FILE, entry)


# ========================================
# LOG READERS (for Analytics Dashboard)
# ========================================

def get_search_logs(limit: int = None) -> List[dict]:
    """Get search log entries"""
    return _read_logs(SEARCH_LOG_FILE, limit)


def get_security_logs(limit: int = None) -> List[dict]:
    """Get security log entries"""
    return _read_logs(SECURITY_LOG_FILE, limit)


def get_performance_logs(limit: int = None) -> List[dict]:
    """Get performance log entries"""
    return _read_logs(PERFORMANCE_LOG_FILE, limit)


def get_log_stats() -> Dict:
    """Get summary statistics from all logs — used by Analytics Dashboard"""
    search_logs = get_search_logs()
    security_logs = get_security_logs()
    performance_logs = get_performance_logs()
    
    # Search stats
    search_queries = [e for e in search_logs if e.get("event_type") == "search_query"]
    no_result_queries = [e for e in search_logs if e.get("event_type") == "no_results"]
    
    # Unique queries
    unique_queries = set(e.get("query", "").lower().strip() for e in search_queries)
    
    # Queries by user role
    role_counts = {}
    for entry in search_queries:
        role = entry.get("user_role", "Unknown")
        role_counts[role] = role_counts.get(role, 0) + 1
    
    # Queries by department
    dept_counts = {}
    for entry in search_queries:
        for dept in entry.get("departments_filter", []):
            dept_counts[dept] = dept_counts.get(dept, 0) + 1
    
    # Top queries
    query_freq = {}
    for entry in search_queries:
        q = entry.get("query", "").lower().strip()
        query_freq[q] = query_freq.get(q, 0) + 1
    top_queries = sorted(query_freq.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Average results per query
    result_counts = [e.get("result_count", 0) for e in search_queries]
    avg_results = sum(result_counts) / len(result_counts) if result_counts else 0
    
    # Average latency
    latencies = [e.get("search_latency_ms", 0) for e in search_queries if e.get("search_latency_ms")]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    
    # Security stats
    confidential_accesses = [e for e in security_logs if e.get("event_type") == "confidential_access"]
    user_logins = [e for e in security_logs if e.get("event_type") == "user_login"]
    
    return {
        "total_searches": len(search_queries),
        "unique_queries": len(unique_queries),
        "no_result_searches": len(no_result_queries),
        "zero_result_rate": len(no_result_queries) / max(len(search_queries), 1) * 100,
        "avg_results_per_query": round(avg_results, 1),
        "avg_search_latency_ms": round(avg_latency, 1),
        "searches_by_role": role_counts,
        "searches_by_department": dept_counts,
        "top_queries": top_queries,
        "total_logins": len(user_logins),
        "confidential_accesses": len(confidential_accesses),
        "total_performance_events": len(performance_logs)
    }


def clear_logs():
    """Clear all log files — for testing/reset"""
    for filepath in [SEARCH_LOG_FILE, SECURITY_LOG_FILE, PERFORMANCE_LOG_FILE]:
        if filepath.exists():
            filepath.unlink()
    _ensure_log_dir()
