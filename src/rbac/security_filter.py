"""
Security Filter Builder for Azure AI Search

Converts user permissions into OData filter expressions that Azure AI Search
can apply at query time. This ensures unauthorized documents are NEVER returned
in search results — filtering happens at the search engine level, not in the app.

Why server-side filtering matters:
    - Documents are filtered BEFORE reaching the application
    - No risk of accidental data leakage in app code
    - Consistent enforcement across all search queries
    - Better performance (fewer results transferred)
"""

from typing import List, Optional
from src.rbac.roles import User


def build_security_filter(user: User, departments: List[str] = None) -> Optional[str]:
    """
    Build OData filter expression for Azure AI Search based on user permissions.
    
    Combines role-based security filtering with optional department filtering
    from the UI sidebar.
    
    Args:
        user: Authenticated user with role and department info
        departments: Additional department filter from UI (optional)
    
    Returns:
        OData filter string for Azure AI Search, or None if no filter needed
    
    Examples:
        Admin user, no dept filter:
            -> None (no filter = full access)
        
        HR Staff, no dept filter:
            -> "(security_level eq 'Public') or (security_level eq 'Department' and department eq 'HR')"
        
        Employee, filtering Sales + IT:
            -> "security_level eq 'Public' and (department eq 'Sales' or department eq 'IT')"
    """
    
    # Admin gets full access — no security filter
    if user.role == "Admin":
        # Still apply department UI filter if selected
        if departments:
            dept_filter = _build_department_filter(departments)
            return dept_filter
        return None
    
    # Build security-level conditions based on user role
    security_conditions = []
    
    # 1. Public documents — always accessible
    security_conditions.append("security_level eq 'Public'")
    
    # 2. Department-level documents — only for user's departments
    accessible_depts = user.accessible_departments
    if accessible_depts:
        # Intersect with UI-selected departments if any
        if departments:
            accessible_depts = [d for d in accessible_depts if d in departments]
        
        if accessible_depts:
            dept_conditions = [f"department eq '{dept}'" for dept in accessible_depts]
            dept_filter = " or ".join(dept_conditions)
            security_conditions.append(
                f"(security_level eq 'Department' and ({dept_filter}))"
            )
    
    # 3. Confidential documents — only for authorized roles
    if user.can_access_confidential:
        conf_depts = user.accessible_departments
        if departments:
            conf_depts = [d for d in conf_depts if d in departments]
        
        if conf_depts:
            dept_conditions = [f"department eq '{dept}'" for dept in conf_depts]
            dept_filter = " or ".join(dept_conditions)
            security_conditions.append(
                f"(security_level eq 'Confidential' and ({dept_filter}))"
            )
    
    # 4. Check allowed_roles field (explicit role-based access)
    role_condition = f"allowed_roles/any(r: r eq '{user.role}') or allowed_roles/any(r: r eq 'All')"
    
    # Combine: (security filter) AND (role filter)
    security_filter = " or ".join(security_conditions)
    final_filter = f"({security_filter}) and ({role_condition})"
    
    # Apply additional department UI filter
    if departments:
        ui_dept_conditions = [f"department eq '{dept}'" for dept in departments]
        ui_dept_filter = " or ".join(ui_dept_conditions)
        final_filter = f"({final_filter}) and ({ui_dept_filter})"
    
    return final_filter


def _build_department_filter(departments: List[str]) -> Optional[str]:
    """Build simple department filter for admin users"""
    if not departments:
        return None
    dept_conditions = [f"department eq '{dept}'" for dept in departments]
    return " or ".join(dept_conditions)


def get_filter_summary(user: User, departments: List[str] = None) -> dict:
    """
    Get human-readable summary of what the user can see.
    Useful for UI display and debugging.
    
    Args:
        user: Authenticated user
        departments: UI department filter
    
    Returns:
        Dictionary with access summary
    """
    accessible_depts = user.accessible_departments
    if departments:
        visible_depts = [d for d in accessible_depts if d in departments]
    else:
        visible_depts = accessible_depts
    
    return {
        "user": user.display_name,
        "role": user.role,
        "security_levels": user.accessible_security_levels,
        "departments_with_access": accessible_depts,
        "currently_viewing": visible_depts if visible_depts else ["Public docs only"],
        "confidential_access": user.can_access_confidential,
        "note": _get_access_note(user)
    }


def _get_access_note(user: User) -> str:
    """Generate access note for UI display"""
    if user.role == "Admin":
        return "Full access to all documents across all departments"
    
    if user.role == "Manager":
        depts = ", ".join(user.departments) if user.departments else "None"
        return f"Manager access to {depts} department(s) including confidential"
    
    if user.role == "Employee":
        return "Access limited to Public documents only"
    
    dept = user.accessible_departments[0] if user.accessible_departments else "None"
    conf = " + Confidential" if user.can_access_confidential else ""
    return f"Access to Public + {dept} department documents{conf}"
