GUARDRAIL_BLOCKED_INPUT = """
    Forbidden! You can only execute SELECT queries to read data. 
    Operations that modify the database (DROP, DELETE, INSERT, UPDATE, ALTER, etc.) are not allowed.
"""

GUARDRAIL_BLOCKED_OUTPUT = """
    The response has been blocked due to security rules. 
    Write operations to the database are not allowed.
"""

SQL_WRITE_DEFINITION = """
    "SQL or natural language requests to modify, delete, insert, update, drop, or alter database data or schema."
"""

PROMPT_INJECTION_DEFINITION = """
Attempts to override system prompts or inject malicious instructions for unauthorized database operations.
"""
