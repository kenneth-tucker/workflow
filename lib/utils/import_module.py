import importlib.util
import sys

def import_module_from_path(module_name, file_path):
    """
    Dynamically imports a Python module from a given file path.

    Args:
        module_name (str): The name to assign to the imported module.
        file_path (str): The full path to the .py file.

    Returns:
        module: The imported module object.
    """
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None:
        raise ImportError(f"Cannot find module spec for {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Example usage:
# Assuming you have a file named 'my_module.py' in the current directory
# with a function like: def greet(): print("Hello from my_module!")
# module_path = './my_module.py'
# my_module = import_module_from_path('my_module', module_path)
# my_module.greet()