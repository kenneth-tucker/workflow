"""
This module defines custom exception classes for the workflow library.
"""

class WorkflowError(Exception):
    """
    Base class for all workflow-related exceptions.
    """
    pass

class ConfigError(WorkflowError):
    """
    Exception raised for errors in the configuration file.
    """
    pass
