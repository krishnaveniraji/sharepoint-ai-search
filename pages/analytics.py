"""
Analytics Dashboard for SharePoint AI Knowledge Assistant

Feature 6: Analytics Dashboard
Visualizes telemetry data collected from search queries, user sessions,
security events, and performance metrics.

Sections:
1. Key Metrics (KPIs at a glance)
2. Search Trends (queries over time, popular queries)
3. User Activity (searches by role, active users)
4. Department Usage (which departments are searched most)
5. Security Overview (confidential accesses, login activity)
6. Performance Metrics (search latency, embedding time)
7. Recent Activity Log (raw event feed)

Run: streamlit run pages/analytics.py
Or navigate via sidebar if using multi-page Streamlit app.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from collections import Counter
from src.telemetry import get_search_logs, get_security_logs, get_performance_logs, get_log_stats

# Page configuration
st.set_page_config(
    page_title="Analytics Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Analytics Dashboard")
st.markdown("*Search usage, security events, and performance monitoring*")
st.markdown("---")


# ========================================
# LOAD DATA
# ========================================

@st.cache_data(ttl=30)  # Refresh every 30 seconds
def load_all_data():
    """Load all telemetry data"""
    search_logs = get_search_logs()
    security_logs = get_security_logs()
    performance_logs = get_performance_logs()
    stats = get_log_stats()
    return search_logs, security_logs, performance_logs, stats


search_logs, security_logs, performance_logs, stats = load_all_data()

# Check if we have data
if stats["total_searches"] == 0:
    st.warning("⚠️ No search data yet. Use the main search app to generate telemetry data, then come back here.")
    st.info("💡 Try doing 5-10 searches with different users and queries to populate the dashboard.")
    st.stop()


# ========================================
# SECTION 1: KEY METRICS (KPIs)
# ========================================

st.header("🎯 Key Metrics")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Total Searches", stats["total_searches"])

with col2:
    st.metric("Unique Queries", stats["unique_queries"])

with col3:
    zero_rate = stats["zero_result_rate"]
    st.metric("Zero-Result Rate", f"{zero_rate:.1f}%",
              delta=f"{'Good' if zero_rate < 20 else 'Needs improvement'}",
              delta_color="normal" if zero_rate < 20 else "inverse")

with col4:
    st.metric("Avg Results/Query", stats["avg_results_per_query"])

with col5:
    latency = stats["avg_search_latency_ms"]
    st.metric("Avg Latency", f"{latency:.0f}ms",
              delta="Fast" if latency < 2000 else "Slow",
              delta_color="normal" if latency < 2000 else "inverse")

st.markdown("---")


# ========================================
# SECTION 2: SEARCH TRENDS
# ========================================

st.header("🔍 Search Trends")

col_left, col_right = st.columns(2)

# Searches over time
with col_left:
    st.subheader("Searches Over Time")
    
    search_queries = [e for e in search_logs if e.get("event_type") == "search_query"]
    
    if search_queries:
        # Parse timestamps
        for entry in search_queries:
            try:
                entry["_parsed_time"] = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
            except:
                entry["_parsed_time"] = datetime.now()
        
        df_searches = pd.DataFrame(search_queries)
        df_searches["hour"] = df_searches["_parsed_time"].apply(lambda x: x.strftime("%Y-%m-%d %H:00"))
        
        hourly_counts = df_searches.groupby("hour").size().reset_index(name="searches")
        
        fig_timeline = px.bar(
            hourly_counts, x="hour", y="searches",
            title="Search Volume by Hour",
            labels={"hour": "Time", "searches": "Number of Searches"},
            color_discrete_sequence=["#1f77b4"]
        )
        fig_timeline.update_layout(height=350, xaxis_tickangle=-45)
        st.plotly_chart(fig_timeline, use_container_width=True)

# Top queries
with col_right:
    st.subheader("Top Queries")
    
    if stats["top_queries"]:
        top_q_df = pd.DataFrame(stats["top_queries"], columns=["Query", "Count"])
        
        fig_queries = px.bar(
            top_q_df, x="Count", y="Query",
            orientation="h",
            title="Most Popular Searches",
            color_discrete_sequence=["#2ca02c"]
        )
        fig_queries.update_layout(height=350, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_queries, use_container_width=True)
    else:
        st.info("Not enough query data yet.")


st.markdown("---")


# ========================================
# SECTION 3: USER ACTIVITY
# ========================================

st.header("👥 User Activity")

col_left2, col_right2 = st.columns(2)

# Searches by role
with col_left2:
    st.subheader("Searches by Role")
    
    if stats["searches_by_role"]:
        role_df = pd.DataFrame(
            list(stats["searches_by_role"].items()),
            columns=["Role", "Searches"]
        ).sort_values("Searches", ascending=False)
        
        fig_roles = px.pie(
            role_df, values="Searches", names="Role",
            title="Search Distribution by User Role",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_roles.update_layout(height=350)
        st.plotly_chart(fig_roles, use_container_width=True)

# Results distribution
with col_right2:
    st.subheader("Results per Query")
    
    result_counts = [e.get("result_count", 0) for e in search_queries]
    if result_counts:
        fig_results = px.histogram(
            x=result_counts,
            nbins=max(result_counts) + 1 if result_counts else 5,
            title="Distribution of Results per Query",
            labels={"x": "Number of Results", "y": "Frequency"},
            color_discrete_sequence=["#ff7f0e"]
        )
        fig_results.update_layout(height=350)
        st.plotly_chart(fig_results, use_container_width=True)


st.markdown("---")


# ========================================
# SECTION 4: DEPARTMENT USAGE
# ========================================

st.header("🏢 Department Usage")

col_left3, col_right3 = st.columns(2)

with col_left3:
    st.subheader("Searches by Department")
    
    if stats["searches_by_department"]:
        dept_df = pd.DataFrame(
            list(stats["searches_by_department"].items()),
            columns=["Department", "Searches"]
        ).sort_values("Searches", ascending=False)
        
        fig_depts = px.bar(
            dept_df, x="Department", y="Searches",
            title="Search Volume by Department",
            color="Department",
            color_discrete_map={
                "HR": "#1f77b4", "Finance": "#2ca02c",
                "IT": "#9467bd", "Sales": "#ff7f0e", "Legal": "#d62728"
            }
        )
        fig_depts.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig_depts, use_container_width=True)

# Security levels in results
with col_right3:
    st.subheader("Security Levels in Results")
    
    all_security_levels = []
    for entry in search_queries:
        levels = entry.get("top_security_levels", [])
        all_security_levels.extend(levels)
    
    if all_security_levels:
        level_counts = Counter(all_security_levels)
        level_df = pd.DataFrame(
            list(level_counts.items()),
            columns=["Security Level", "Count"]
        )
        
        fig_security = px.pie(
            level_df, values="Count", names="Security Level",
            title="Documents Returned by Security Level",
            color="Security Level",
            color_discrete_map={
                "Public": "#2ca02c", "Department": "#1f77b4", "Confidential": "#d62728"
            }
        )
        fig_security.update_layout(height=350)
        st.plotly_chart(fig_security, use_container_width=True)


st.markdown("---")


# ========================================
# SECTION 5: SECURITY OVERVIEW
# ========================================

st.header("🔒 Security Overview")

col_sec1, col_sec2, col_sec3 = st.columns(3)

with col_sec1:
    st.metric("Total User Logins", stats["total_logins"])

with col_sec2:
    st.metric("Confidential Accesses", stats["confidential_accesses"])

with col_sec3:
    st.metric("No-Result Searches", stats["no_result_searches"])

# Confidential access details
confidential_events = [e for e in security_logs if e.get("event_type") == "confidential_access"]

if confidential_events:
    st.subheader("Recent Confidential Document Accesses")
    
    conf_data = []
    for event in confidential_events[-20:]:  # Last 20
        conf_data.append({
            "Time": event.get("timestamp", "")[:19],
            "User": event.get("user_email", ""),
            "Role": event.get("user_role", ""),
            "Document": event.get("details", {}).get("document_title", "Unknown"),
            "Department": event.get("details", {}).get("department", "Unknown")
        })
    
    st.dataframe(
        pd.DataFrame(conf_data),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No confidential document accesses logged yet.")


st.markdown("---")


# ========================================
# SECTION 6: PERFORMANCE METRICS
# ========================================

st.header("⚡ Performance Metrics")

col_perf1, col_perf2 = st.columns(2)

with col_perf1:
    st.subheader("Search Latency")
    
    search_perf = [e for e in performance_logs if e.get("operation") == "search"]
    
    if search_perf:
        latencies = [e.get("latency_ms", 0) for e in search_perf]
        
        fig_latency = px.histogram(
            x=latencies,
            nbins=20,
            title="Search Latency Distribution (ms)",
            labels={"x": "Latency (ms)", "y": "Frequency"},
            color_discrete_sequence=["#17becf"]
        )
        fig_latency.update_layout(height=300)
        st.plotly_chart(fig_latency, use_container_width=True)
        
        # Latency stats
        st.markdown(f"**Min:** {min(latencies):.0f}ms | "
                    f"**Avg:** {sum(latencies)/len(latencies):.0f}ms | "
                    f"**Max:** {max(latencies):.0f}ms")
    else:
        st.info("No performance data yet.")

with col_perf2:
    st.subheader("Embedding Generation Time")
    
    embed_perf = [e for e in performance_logs if e.get("operation") == "embedding_generation"]
    
    if embed_perf:
        embed_latencies = [e.get("latency_ms", 0) for e in embed_perf]
        
        fig_embed = px.histogram(
            x=embed_latencies,
            nbins=20,
            title="Embedding Generation Latency (ms)",
            labels={"x": "Latency (ms)", "y": "Frequency"},
            color_discrete_sequence=["#bcbd22"]
        )
        fig_embed.update_layout(height=300)
        st.plotly_chart(fig_embed, use_container_width=True)
        
        st.markdown(f"**Min:** {min(embed_latencies):.0f}ms | "
                    f"**Avg:** {sum(embed_latencies)/len(embed_latencies):.0f}ms | "
                    f"**Max:** {max(embed_latencies):.0f}ms")
    else:
        st.info("No embedding performance data yet.")


st.markdown("---")


# ========================================
# SECTION 7: RECENT ACTIVITY LOG
# ========================================

st.header("📋 Recent Activity")

# Combine all logs and sort by timestamp
all_events = []

for entry in search_logs[-10:]:
    all_events.append({
        "Time": entry.get("timestamp", "")[:19],
        "Type": "🔍 " + entry.get("event_type", ""),
        "User": entry.get("user_email", ""),
        "Details": entry.get("query", "")[:50] + (f" → {entry.get('result_count', 0)} results" 
                   if entry.get("event_type") == "search_query" else "")
    })

for entry in security_logs[-10:]:
    event_type = entry.get("event_type", "")
    icon = {"user_login": "🔐", "confidential_access": "🔒"}.get(event_type, "🛡️")
    details = entry.get("details", {})
    detail_str = details.get("document_title", "") or f"Depts: {', '.join(details.get('departments', []))}"
    
    all_events.append({
        "Time": entry.get("timestamp", "")[:19],
        "Type": f"{icon} {event_type}",
        "User": entry.get("user_email", ""),
        "Details": detail_str[:60]
    })

# Sort by time descending
all_events.sort(key=lambda x: x["Time"], reverse=True)

if all_events:
    st.dataframe(
        pd.DataFrame(all_events[:20]),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No activity logged yet.")


# ========================================
# REFRESH & CONTROLS
# ========================================

st.markdown("---")

col_ctrl1, col_ctrl2 = st.columns([1, 4])

with col_ctrl1:
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

with col_ctrl2:
    st.caption(
        f"Dashboard showing {stats['total_searches']} searches, "
        f"{stats['total_logins']} logins, "
        f"{stats['confidential_accesses']} confidential accesses. "
        f"Data refreshes every 30 seconds."
    )

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 12px;">
    SharePoint AI Knowledge Assistant — Analytics Dashboard<br>
    Powered by Streamlit + Plotly + Telemetry Engine
</div>
""", unsafe_allow_html=True)
