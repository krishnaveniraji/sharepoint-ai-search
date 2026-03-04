"""
Document Security Classifier

Automatically assigns security levels and allowed roles to documents
during indexing based on filename patterns and department rules.

This replaces the default "General" security level with proper
classifications that enable role-based filtering at search time.

Security Classification Rules:
    1. Filename pattern matching (e.g., "confidential", "salary", "budget")
    2. Department-based defaults (e.g., Legal defaults to Department level)
    3. Explicit mapping for known document types
    4. Fallback to Public for unclassified documents
"""

import re
from typing import Dict, List, Tuple

# ========================================
# FILENAME PATTERN RULES
# ========================================

# Patterns that indicate Confidential documents
CONFIDENTIAL_PATTERNS = [
    r"confidential",
    r"salary",
    r"compensation",
    r"termination",
    r"disciplinary",
    r"performance.*(review|rating)",
    r"merger",
    r"acquisition",
    r"board.*(minutes|meeting)",
    r"nda",
    r"non.?disclosure",
    r"settlement",
    r"litigation",
    r"audit.*(finding|report)",
    r"security.*(incident|breach)",
    r"revenue.*(forecast|projection)",
    r"budget.*(final|approved)",
    r"strategic.*(plan|initiative)",
    r"executive",
]

# Patterns that indicate Department-level documents
DEPARTMENT_PATTERNS = [
    r"internal",
    r"procedure",
    r"process",
    r"guideline",
    r"handbook",
    r"training",
    r"onboarding",
    r"team.*(meeting|notes)",
    r"quarterly.*(review|report)",
    r"kpi",
    r"sop",
    r"workflow",
    r"standard.*(operating|procedure)",
    r"draft",
    r"template",
]

# Patterns that indicate Public documents
PUBLIC_PATTERNS = [
    r"public",
    r"general.*(policy|info)",
    r"faq",
    r"employee.*(handbook|guide)",
    r"welcome",
    r"holiday",
    r"leave.*(policy|calendar)",
    r"dress.?code",
    r"code.?of.?conduct",
    r"office.*(location|hours)",
    r"helpdesk",
    r"contact",
]


# ========================================
# DEPARTMENT DEFAULT LEVELS
# ========================================

# Default security level by department (when no pattern matches)
DEPARTMENT_DEFAULTS = {
    "HR": "Department",        # HR docs often contain sensitive info
    "Finance": "Department",   # Financial data is department-restricted
    "IT": "Department",        # IT procedures may include security details
    "Sales": "Department",     # Sales data is competitive info
    "Legal": "Confidential",   # Legal documents default to confidential
}


# ========================================
# ROLE MAPPINGS
# ========================================

# Allowed roles by security level and department
ALLOWED_ROLES_MAP = {
    "Public": ["All"],
    "Department": {
        "HR": ["Admin", "Manager", "HR_Staff"],
        "Finance": ["Admin", "Manager", "Finance_Staff"],
        "IT": ["Admin", "Manager", "IT_Staff"],
        "Sales": ["Admin", "Manager", "Sales_Staff"],
        "Legal": ["Admin", "Manager", "Legal_Staff"],
    },
    "Confidential": {
        "HR": ["Admin", "Manager"],
        "Finance": ["Admin", "Manager"],
        "IT": ["Admin", "Manager"],
        "Sales": ["Admin", "Manager"],
        "Legal": ["Admin", "Manager", "Legal_Staff"],
    }
}


def classify_document(filename: str, department: str) -> Dict:
    """
    Classify a document's security level based on its filename and department.
    
    Args:
        filename: Document filename (e.g., "salary_bands_2026.pdf")
        department: Department the document belongs to
    
    Returns:
        Dictionary with:
            - security_level: "Public", "Department", or "Confidential"
            - is_confidential: Boolean
            - allowed_roles: List of roles that can access this document
    """
    filename_lower = filename.lower()
    
    # Check Confidential patterns first (highest priority)
    for pattern in CONFIDENTIAL_PATTERNS:
        if re.search(pattern, filename_lower):
            return _build_classification("Confidential", department)
    
    # Check Public patterns (second priority)
    for pattern in PUBLIC_PATTERNS:
        if re.search(pattern, filename_lower):
            return _build_classification("Public", department)
    
    # Check Department patterns
    for pattern in DEPARTMENT_PATTERNS:
        if re.search(pattern, filename_lower):
            return _build_classification("Department", department)
    
    # Fallback to department default
    default_level = DEPARTMENT_DEFAULTS.get(department, "Public")
    return _build_classification(default_level, department)


def _build_classification(security_level: str, department: str) -> Dict:
    """Build classification result dictionary"""
    
    # Get allowed roles
    if security_level == "Public":
        allowed_roles = ["All"]
    else:
        level_map = ALLOWED_ROLES_MAP.get(security_level, {})
        if isinstance(level_map, dict):
            allowed_roles = level_map.get(department, ["Admin"])
        else:
            allowed_roles = level_map
    
    return {
        "security_level": security_level,
        "is_confidential": security_level == "Confidential",
        "allowed_roles": allowed_roles
    }


def classify_batch(documents: List[Dict]) -> List[Dict]:
    """
    Classify a batch of documents, adding security fields to each.
    
    Args:
        documents: List of document dicts with 'title' and 'department' keys
    
    Returns:
        Same documents with security_level, is_confidential, allowed_roles added
    """
    for doc in documents:
        classification = classify_document(
            filename=doc.get('title', doc.get('name', '')),
            department=doc.get('department', 'Unknown')
        )
        doc.update(classification)
    
    return documents


# ========================================
# TESTING / DEMO
# ========================================

if __name__ == "__main__":
    # Test with sample documents
    test_docs = [
        ("Employee_Leave_Policy.pdf", "HR"),
        ("Salary_Bands_2026.xlsx", "HR"),
        ("Performance_Review_Template.docx", "HR"),
        ("General_FAQ.pdf", "HR"),
        ("Q4_Revenue_Forecast.xlsx", "Finance"),
        ("Budget_Final_2026.pdf", "Finance"),
        ("Expense_Guidelines.pdf", "Finance"),
        ("Security_Incident_Response.pdf", "IT"),
        ("IT_Helpdesk_Contact.txt", "IT"),
        ("NDA_Template.docx", "Legal"),
        ("Code_of_Conduct.pdf", "Legal"),
        ("Sales_Team_Meeting_Notes.docx", "Sales"),
        ("Client_Onboarding_Process.pdf", "Sales"),
    ]
    
    print("=" * 70)
    print("DOCUMENT SECURITY CLASSIFICATION")
    print("=" * 70)
    print(f"\n{'Document':<45} {'Dept':<10} {'Level':<15} {'Roles'}")
    print("-" * 100)
    
    for filename, dept in test_docs:
        result = classify_document(filename, dept)
        roles = ", ".join(result['allowed_roles'])
        level = result['security_level']
        conf = "🔒" if result['is_confidential'] else "  "
        print(f"{conf} {filename:<43} {dept:<10} {level:<15} {roles}")
