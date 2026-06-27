"""
Sample Enterprise Dataset for MultiMind AI Demo.
Realistic HR/Policy documents to demonstrate all features.
"""

SAMPLE_DOCS = [
    {
        "name": "Employee_Handbook_2022.pdf",
        "content": """# Employee Handbook 2022

## Leave Policy
Employees are entitled to 20 days of paid time off (PTO) per year.
Unused days may be carried forward up to 5 days.

## Remote Work
Remote work is allowed up to 2 days per week with manager approval.

## Code of Conduct
All employees must follow the company code of conduct.
Violations may result in disciplinary action.

Version: 2022.1
Last Updated: January 2022""",
        "metadata": {"type": "policy", "year": 2022, "source": "HR"}
    },
    {
        "name": "Employee_Handbook_2023.pdf", 
        "content": """# Employee Handbook 2023

## Leave Policy
Employees are entitled to 22 days of paid time off (PTO) per year.
Unused days may be carried forward up to 10 days.

## Remote Work
Remote work is allowed up to 3 days per week with manager approval.

## Code of Conduct
All employees must follow the company code of conduct.
Violations may result in disciplinary action or termination.

Version: 2023.1
Last Updated: January 2023""",
        "metadata": {"type": "policy", "year": 2023, "source": "HR"}
    },
    {
        "name": "Employee_Handbook_2024.pdf",
        "content": """# Employee Handbook 2024

## Leave Policy
Employees are entitled to 24 days of paid time off (PTO) per year.
Unused days may be carried forward up to 15 days.
New hires get pro-rated PTO based on start date.

## Remote Work
Remote work is allowed up to 4 days per week with manager approval.
Unpaid remote work available for exceptional circumstances.

## Salary Structure
- Level 1: $70,000 - $90,000
- Level 2: $90,000 - $120,000
- Level 3: $120,000 - $160,000

Version: 2024.1
Last Updated: January 2024""",
        "metadata": {"type": "policy", "year": 2024, "source": "HR"}
    },
    {
        "name": "IT_Security_Policy.pdf",
        "content": """# IT Security Policy

## Password Requirements
- Minimum 12 characters
- Must include numbers and special characters
- Expires every 90 days

## Access Control
Admin access requires approval from Security Team.
All access logged and audited monthly.

## Incident Reporting
Report security incidents within 24 hours to security@company.com""",
        "metadata": {"type": "security", "department": "IT"}
    },
    {
        "name": "Performance_Review_Process.pdf",
        "content": """# Performance Review Process

## Review Cycle
Annual reviews conducted in Q1.
Mid-year check-ins optional but recommended.

## Rating Scale
1 = Needs Improvement
2 = Meets Expectations  
3 = Exceeds Expectations
4 = Exceptional

## Promotion Criteria
Rating of 3.5+ average over 12 months."""
        "metadata": {"type": "process", "department": "HR"}
    }
]


def get_sample_dataset() -> list:
    """Get the sample dataset for demos."""
    return SAMPLE_DOCS


def get_evolution_queries() -> list:
    """Get queries that demonstrate knowledge evolution."""
    return [
        "How has our leave policy changed over the years?",
        "Show me the evolution of PTO policy",
        "Compare the 2022 and 2024 handbooks",
        "What changed in our remote work policy?",
    ]


def get_conflict_queries() -> list:
    """Get queries that might show conflicts."""
    return [
        "How many PTO days do employees get?",  # Will show evolution
        "What is the password length requirement?",  # Single source
        "Who sets salary levels?",  # Might conflict
    ]