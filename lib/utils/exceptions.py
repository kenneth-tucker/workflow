# Types of exceptions that the workflow library might raise
class WorkflowError(Exception):
    """Base class for all workflow-related exceptions."""
    pass

class ConfigError(WorkflowError):
    """Exception raised for errors in the configuration file."""
    pass
