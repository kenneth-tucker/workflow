"""
Tests for lib/utils/import_module.py (dynamic import of a .py file by path,
used by ExperimentConfig to load a researcher-provided part_types.py).
"""
import sys
import pytest
from lib.utils.import_module import import_module_from_path


class TestImportModuleFromPath:
    def test_imports_module_and_exposes_its_attributes(self, tmp_path):
        module_path = tmp_path / "sample_module.py"
        module_path.write_text("X = 42\n\ndef f():\n    return 'hi'\n", encoding="utf-8")

        module = import_module_from_path("test_sample_module", str(module_path))

        assert module.X == 42
        assert module.f() == "hi"

    def test_registers_module_in_sys_modules_under_given_name(self, tmp_path):
        module_path = tmp_path / "registered_module.py"
        module_path.write_text("X = 1\n", encoding="utf-8")

        module = import_module_from_path("test_registered_module", str(module_path))

        assert sys.modules["test_registered_module"] is module

    def test_raises_error_for_nonexistent_file_path(self, tmp_path):
        missing_path = tmp_path / "does_not_exist.py"

        with pytest.raises(FileNotFoundError):
            import_module_from_path("test_missing_module", str(missing_path))

    def test_raises_error_when_imported_file_has_a_syntax_error(self, tmp_path):
        module_path = tmp_path / "broken_module.py"
        module_path.write_text("def bad(:\n", encoding="utf-8")

        with pytest.raises(SyntaxError):
            import_module_from_path("test_broken_module", str(module_path))
