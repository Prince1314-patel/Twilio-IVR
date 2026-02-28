"""
Property-based tests for backend refactoring directory structure.

Feature: backend-refactoring

These tests verify that the refactored directory structure meets the requirements
and maintains proper organization.
"""

import unittest
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
from hypothesis import given, strategies as st, settings

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestRefactoringDirectoryStructure(unittest.TestCase):
    """Property-based tests for refactored directory structure."""
    
    def setUp(self):
        """Set up test environment."""
        self.backend_root = Path(__file__).parent.parent
        self.app_root = self.backend_root / "app"
    
    def test_directory_structure_correctness_property(self):
        """
        Property 1: Directory Structure Correctness
        
        For any required directory in the target architecture, it should exist
        with proper Python package structure (__init__.py files).
        
        **Feature: backend-refactoring, Property 1: Directory Structure Correctness**
        **Validates: Requirements 1.1, 1.2, 2.1, 3.1, 4.1**
        """
        # Define the expected directory structure based on design specification
        expected_directories = [
            # API layer
            "app/apis",
            
            # AI system
            "app/ai",
            "app/ai/agents", 
            "app/ai/llm",
            "app/ai/prompts",
            "app/ai/services",
            "app/ai/utils",
            
            # Database layer
            "app/database",
            "app/database/tools",
            
            # Core infrastructure (already exists)
            "app/core",
            
            # Application utilities
            "app/utils"
        ]
        
        # Test 1: All required directories should exist
        for dir_path in expected_directories:
            full_path = self.backend_root / dir_path
            self.assertTrue(
                full_path.exists() and full_path.is_dir(),
                f"Required directory {dir_path} does not exist"
            )
        
        # Test 2: All directories should be proper Python packages
        for dir_path in expected_directories:
            init_file = self.backend_root / dir_path / "__init__.py"
            self.assertTrue(
                init_file.exists() and init_file.is_file(),
                f"Directory {dir_path} is missing __init__.py file"
            )
        
        # Test 3: Core directories should maintain existing structure
        core_files = [
            "app/core/config.py",
            "app/core/logger_config.py", 
            "app/core/websocket_manager.py"
        ]
        
        for file_path in core_files:
            full_path = self.backend_root / file_path
            self.assertTrue(
                full_path.exists() and full_path.is_file(),
                f"Core file {file_path} should be preserved"
            )
        
        # Test 4: Archive directory should remain unchanged
        archive_path = self.backend_root / "archive"
        self.assertTrue(
            archive_path.exists() and archive_path.is_dir(),
            "Archive directory should be preserved"
        )
        
        legacy_files_path = archive_path / "legacy_files"
        self.assertTrue(
            legacy_files_path.exists() and legacy_files_path.is_dir(),
            "Archive/legacy_files directory should be preserved"
        )
    
    def test_api_layer_organization_property(self):
        """
        Test that API routes are properly organized under apis/ directory.
        
        **Feature: backend-refactoring, Property 1: Directory Structure Correctness**
        **Validates: Requirements 1.1**
        """
        apis_dir = self.app_root / "apis"
        
        # APIs directory should exist
        self.assertTrue(apis_dir.exists() and apis_dir.is_dir())
        
        # Should have __init__.py
        init_file = apis_dir / "__init__.py"
        self.assertTrue(init_file.exists() and init_file.is_file())
        
        # Should be ready to receive router files (chat.py, voice.py, voice_stream.py)
        # Note: Files will be moved in later tasks, so we just verify structure is ready
        self.assertTrue(apis_dir.is_dir(), "APIs directory should be ready for router files")
    
    def test_ai_components_organization_property(self):
        """
        Test that AI components are properly organized under ai/ directory.
        
        **Feature: backend-refactoring, Property 1: Directory Structure Correctness**
        **Validates: Requirements 2.1**
        """
        ai_dir = self.app_root / "ai"
        
        # AI directory should exist
        self.assertTrue(ai_dir.exists() and ai_dir.is_dir())
        
        # All AI subdirectories should exist
        ai_subdirs = ["agents", "llm", "prompts", "services", "utils"]
        for subdir in ai_subdirs:
            subdir_path = ai_dir / subdir
            self.assertTrue(
                subdir_path.exists() and subdir_path.is_dir(),
                f"AI subdirectory {subdir} should exist"
            )
            
            # Each subdirectory should have __init__.py
            init_file = subdir_path / "__init__.py"
            self.assertTrue(
                init_file.exists() and init_file.is_file(),
                f"AI subdirectory {subdir} should have __init__.py"
            )
    
    def test_database_layer_organization_property(self):
        """
        Test that database components are properly organized under database/ directory.
        
        **Feature: backend-refactoring, Property 1: Directory Structure Correctness**
        **Validates: Requirements 3.1**
        """
        database_dir = self.app_root / "database"
        
        # Database directory should exist
        self.assertTrue(database_dir.exists() and database_dir.is_dir())
        
        # Should have __init__.py
        init_file = database_dir / "__init__.py"
        self.assertTrue(init_file.exists() and init_file.is_file())
        
        # Tools subdirectory should exist
        tools_dir = database_dir / "tools"
        self.assertTrue(tools_dir.exists() and tools_dir.is_dir())
        
        # Tools should have __init__.py
        tools_init = tools_dir / "__init__.py"
        self.assertTrue(tools_init.exists() and tools_init.is_file())
    
    def test_core_infrastructure_preservation_property(self):
        """
        Test that core infrastructure remains in core/ directory.
        
        **Feature: backend-refactoring, Property 1: Directory Structure Correctness**
        **Validates: Requirements 1.2**
        """
        core_dir = self.app_root / "core"
        
        # Core directory should exist
        self.assertTrue(core_dir.exists() and core_dir.is_dir())
        
        # Essential core files should exist
        essential_files = [
            "config.py",
            "logger_config.py",
            "websocket_manager.py"
        ]
        
        for filename in essential_files:
            file_path = core_dir / filename
            self.assertTrue(
                file_path.exists() and file_path.is_file(),
                f"Core file {filename} should be preserved"
            )
    
    def test_archive_preservation_property(self):
        """
        Test that archive directory structure is preserved unchanged.
        
        **Feature: backend-refactoring, Property 1: Directory Structure Correctness**
        **Validates: Requirements 7.1, 7.2, 7.3, 7.4**
        """
        archive_dir = self.backend_root / "archive"
        
        # Archive directory should exist
        self.assertTrue(archive_dir.exists() and archive_dir.is_dir())
        
        # Legacy files directory should exist
        legacy_dir = archive_dir / "legacy_files"
        self.assertTrue(legacy_dir.exists() and legacy_dir.is_dir())
        
        # Some expected legacy files should still exist (unchanged)
        expected_legacy_files = [
            "answer_phone.py",
            "legacy_make_call.py", 
            "make_call.py",
            "run_agent_cli.py",
            "start_app.py",
            "test_integration.py"
        ]
        
        for filename in expected_legacy_files:
            file_path = legacy_dir / filename
            self.assertTrue(
                file_path.exists() and file_path.is_file(),
                f"Legacy file {filename} should be preserved unchanged"
            )
    
    @given(st.sampled_from([
        "apis", "ai", "ai/agents", "ai/llm", "ai/prompts", "ai/services", 
        "ai/utils", "database", "database/tools", "utils"
    ]))
    def test_python_package_structure_property(self, directory_path: str):
        """
        Property test: Any new directory should be a proper Python package.
        
        **Feature: backend-refactoring, Property 1: Directory Structure Correctness**
        **Validates: Requirements 1.1, 1.2, 2.1, 3.1, 4.1**
        """
        full_path = self.app_root / directory_path
        
        # Directory should exist
        self.assertTrue(
            full_path.exists() and full_path.is_dir(),
            f"Directory {directory_path} should exist"
        )
        
        # Should have __init__.py file
        init_file = full_path / "__init__.py"
        self.assertTrue(
            init_file.exists() and init_file.is_file(),
            f"Directory {directory_path} should have __init__.py file"
        )
        
        # __init__.py should be readable
        try:
            with open(init_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Should have some content (at least a docstring)
                self.assertGreater(
                    len(content.strip()), 0,
                    f"__init__.py in {directory_path} should not be empty"
                )
        except Exception as e:
            self.fail(f"Failed to read __init__.py in {directory_path}: {e}")
    
    def test_directory_separation_property(self):
        """
        Test that different concerns are properly separated into different directories.
        
        **Feature: backend-refactoring, Property 1: Directory Structure Correctness**
        **Validates: Requirements 1.5, 8.2, 8.3**
        """
        # Test 1: API layer separation
        apis_dir = self.app_root / "apis"
        self.assertTrue(apis_dir.exists(), "API layer should be separated")
        
        # Test 2: AI components separation
        ai_dir = self.app_root / "ai"
        self.assertTrue(ai_dir.exists(), "AI components should be separated")
        
        # Test 3: Database layer separation
        database_dir = self.app_root / "database"
        self.assertTrue(database_dir.exists(), "Database layer should be separated")
        
        # Test 4: Core infrastructure separation
        core_dir = self.app_root / "core"
        self.assertTrue(core_dir.exists(), "Core infrastructure should be separated")
        
        # Test 5: Utilities separation
        utils_dir = self.app_root / "utils"
        self.assertTrue(utils_dir.exists(), "Utilities should be separated")
        
        # Test 6: Each directory should serve a distinct purpose
        # (This is validated by the existence and proper organization)
        distinct_directories = [apis_dir, ai_dir, database_dir, core_dir, utils_dir]
        
        for directory in distinct_directories:
            self.assertTrue(
                directory.exists() and directory.is_dir(),
                f"Directory {directory.name} should exist for separation of concerns"
            )
    
    def test_scalability_structure_property(self):
        """
        Test that the directory structure supports scalability and future growth.
        
        **Feature: backend-refactoring, Property 1: Directory Structure Correctness**
        **Validates: Requirements 8.1, 8.5**
        """
        # Test 1: Modular structure allows for easy extension
        ai_dir = self.app_root / "ai"
        ai_subdirs = list(ai_dir.iterdir()) if ai_dir.exists() else []
        
        # Should have multiple AI subdirectories for different concerns
        ai_subdir_names = [d.name for d in ai_subdirs if d.is_dir()]
        expected_ai_subdirs = ["agents", "llm", "prompts", "services", "utils"]
        
        for expected_subdir in expected_ai_subdirs:
            self.assertIn(
                expected_subdir, ai_subdir_names,
                f"AI should have {expected_subdir} subdirectory for modularity"
            )
        
        # Test 2: Database layer is organized for extension
        database_dir = self.app_root / "database"
        if database_dir.exists():
            tools_dir = database_dir / "tools"
            self.assertTrue(
                tools_dir.exists(),
                "Database should have tools subdirectory for extensibility"
            )
        
        # Test 3: Clear layer boundaries support microservice extraction
        layer_directories = ["apis", "ai", "database", "core", "utils"]
        
        for layer in layer_directories:
            layer_path = self.app_root / layer
            self.assertTrue(
                layer_path.exists() and layer_path.is_dir(),
                f"Layer {layer} should exist for clear boundaries"
            )


if __name__ == '__main__':
    unittest.main()