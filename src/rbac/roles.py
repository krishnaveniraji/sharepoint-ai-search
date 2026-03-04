"""
Role-Based Access Control (RBAC) for SharePoint AI Knowledge Assistant

Defines roles, permissions, and security level mappings for enterprise
document access control.

Security Levels:
    - Public: Accessible to all authenticated users
    - Department: Accessible to department members and managers
    - Confidential: Accessible only to specified roles (e.g., Manager, Legal)

Roles:
    - Admin: Full access to all documents across all departments
    - Manager: Access to Public + Department + Confidential in their department(s)
    - HR_Staff / Finance_Staff / IT_Staff / Sales_Staff / Legal_Staff:
        Access to Public + their own Department-level docs
    - Employee: Access to Public documents only
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field


# ========================================
# ROLE DEFINITIONS
# ========================================

# All available roles in the system
AVAILABLE_ROLES = [
    "Admin",
    "Manager",
    "HR_Staff",
    "Finance_Staff",
    "IT_Staff",
    "Sales_Staff",
    "Legal_Staff",
    "Employee"
]

# Security levels from least to most restrictive
SECURITY_LEVELS = ["Public", "Department", "Confidential"]


# ========================================
# ROLE-TO-DEPARTMENT MAPPING
# ========================================

# Which departments each role can access at "Department" security level
ROLE_DEPARTMENT_ACCESS = {
    "Admin": ["HR", "Finance", "IT", "Sales", "Legal"],
    "Manager": [],  # Set dynamically based on assigned departments
    "HR_Staff": ["HR"],
    "Finance_Staff": ["Finance"],
    "IT_Staff": ["IT"],
    "Sales_Staff": ["Sales"],
    "Legal_Staff": ["Legal"],
    "Employee": []  # No department-level access
}

# Which roles can access "Confidential" documents
CONFIDENTIAL_ACCESS_ROLES = ["Admin", "Manager", "Legal_Staff"]


# ========================================
# USER MODEL
# ========================================

@dataclass
class User:
    """Represents an authenticated user with role-based permissions"""
    
    user_id: str
    display_name: str
    email: str
    role: str
    departments: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate role on creation"""
        if self.role not in AVAILABLE_ROLES:
            raise ValueError(f"Invalid role: {self.role}. Must be one of {AVAILABLE_ROLES}")
    
    @property
    def can_access_confidential(self) -> bool:
        """Check if user can access confidential documents"""
        return self.role in CONFIDENTIAL_ACCESS_ROLES
    
    @property
    def accessible_departments(self) -> List[str]:
        """Get list of departments this user can access at Department level"""
        if self.role == "Admin":
            return ["HR", "Finance", "IT", "Sales", "Legal"]
        
        if self.role == "Manager":
            return self.departments if self.departments else []
        
        return ROLE_DEPARTMENT_ACCESS.get(self.role, [])
    
    @property
    def accessible_security_levels(self) -> List[str]:
        """Get security levels this user can access"""
        levels = ["Public"]  # Everyone gets Public
        
        if self.accessible_departments:
            levels.append("Department")
        
        if self.can_access_confidential:
            levels.append("Confidential")
        
        return levels
    
    def can_access_document(self, security_level: str, department: str,
                            allowed_roles: List[str] = None) -> bool:
        """
        Check if user can access a specific document.
        
        Args:
            security_level: Document's security level (Public/Department/Confidential)
            department: Document's department
            allowed_roles: Explicit list of roles allowed (overrides defaults)
        
        Returns:
            True if user has access
        """
        # Admin always has access
        if self.role == "Admin":
            return True
        
        # Check explicit allowed_roles if provided
        if allowed_roles and allowed_roles != ["All"]:
            if self.role in allowed_roles:
                return True
            # If explicit roles are set and user is not in list, deny
            return False
        
        # Public documents - everyone can access
        if security_level == "Public":
            return True
        
        # Department-level documents
        if security_level == "Department":
            return department in self.accessible_departments
        
        # Confidential documents
        if security_level == "Confidential":
            if not self.can_access_confidential:
                return False
            # Confidential + must have department access (unless Admin)
            return department in self.accessible_departments
        
        # Default deny
        return False


# ========================================
# DEMO USERS (for portfolio demonstration)
# ========================================

DEMO_USERS: Dict[str, User] = {
    "admin@veniai.com": User(
        user_id="admin-001",
        display_name="Priya Sharma (Admin)",
        email="admin@veniai.com",
        role="Admin",
        departments=["HR", "Finance", "IT", "Sales", "Legal"]
    ),
    "hr.manager@veniai.com": User(
        user_id="mgr-hr-001",
        display_name="Aisha Khan (HR Manager)",
        email="hr.manager@veniai.com",
        role="Manager",
        departments=["HR"]
    ),
    "finance.manager@veniai.com": User(
        user_id="mgr-fin-001",
        display_name="Rajesh Patel (Finance Manager)",
        email="finance.manager@veniai.com",
        role="Manager",
        departments=["Finance"]
    ),
    "hr.staff@veniai.com": User(
        user_id="staff-hr-001",
        display_name="Sara Ahmed (HR Staff)",
        email="hr.staff@veniai.com",
        role="HR_Staff",
        departments=["HR"]
    ),
    "finance.staff@veniai.com": User(
        user_id="staff-fin-001",
        display_name="Mohammed Ali (Finance Staff)",
        email="finance.staff@veniai.com",
        role="Finance_Staff",
        departments=["Finance"]
    ),
    "it.staff@veniai.com": User(
        user_id="staff-it-001",
        display_name="Deepak Nair (IT Staff)",
        email="it.staff@veniai.com",
        role="IT_Staff",
        departments=["IT"]
    ),
    "sales.staff@veniai.com": User(
        user_id="staff-sales-001",
        display_name="Fatima Hassan (Sales Staff)",
        email="sales.staff@veniai.com",
        role="Sales_Staff",
        departments=["Sales"]
    ),
    "legal.staff@veniai.com": User(
        user_id="staff-legal-001",
        display_name="Ahmad Khalil (Legal Staff)",
        email="legal.staff@veniai.com",
        role="Legal_Staff",
        departments=["Legal"]
    ),
    "employee@veniai.com": User(
        user_id="emp-001",
        display_name="Ravi Kumar (Employee)",
        email="employee@veniai.com",
        role="Employee",
        departments=[]
    ),
}


def get_demo_user(email: str) -> Optional[User]:
    """Get demo user by email"""
    return DEMO_USERS.get(email)


def get_all_demo_users() -> Dict[str, User]:
    """Get all demo users"""
    return DEMO_USERS


def get_user_summary(user: User) -> Dict:
    """Get human-readable summary of user permissions"""
    return {
        "name": user.display_name,
        "role": user.role,
        "departments": user.accessible_departments,
        "security_levels": user.accessible_security_levels,
        "can_access_confidential": user.can_access_confidential
    }
