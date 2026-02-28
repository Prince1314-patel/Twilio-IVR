"""
Property-based tests for layer boundary enforcement in backend refactoring.

Feature: backend-refactoring

These tests verify that the refactored architecture maintains proper layer
boundaries and prevents violations of architectural principles.
"""

import unittest
import os
import sys
import ast
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict
from hypothesis import given, strategies as st, settings

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class LayerBoundaryAnalyzer:
    """Analyzes layer boundaries and import dependencies."""
    
    def __init__(self, app_root: Path):
        self.app_root = app_root
        self.dependencies = defaultdict(set)
        self.layer_mapping = {}
        self.modules = set()
        
        # Define architectural layers (lower number = lower layer)
        self.layers = {
            "database": 1,
            "core": 2,
            "utils": 2,  # Utils can be used by any layer
            "ai": 3,
            "apis": 4,
        }
        
        # Define allowed cross-layer dependencies
        # Format: (higher_layer, lower_layer) - higher can import from lower
        self.allowed_cross_layer = {
            ("apis", "ai"),      # APIs can use AI
            ("apis", "core"),    # APIs can use core
            ("apis", "database"), # APIs can use database
            ("apis", "utils"),   # APIs can use utils
            ("ai", "core"),      # AI can use core
            ("ai", "database"),  # AI can use database tools
            ("ai", "utils"),     # AI can use utils
            ("core", "utils"),   # Core can use utils
            ("database", "utils"), # Database can use utils
            ("database", "core"), # Database can use core (for logging)
        }
    
    def extract_imports_from_file(self, filepath: Path) -> List[str]:
        """Extract all import statements from a Python file."""
        imports = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
        
        except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
            # Skip files that can't be parsed
            pass
        
        return imports
    
    def get_module_layer(self, module_path: str) -> str:
        """Determine which architectural layer a module belongs to."""
        # Remove app. prefix if present
        if module_path.startswith("app."):
            module_path = module_path[4:]
        
        # Extract the top-level directory
        parts = module_path.split(".")
        if parts:
            top_level = parts[0]
            if top_level in self.layers:
                return top_level
        
        return "unknown"
    
    def is_internal_import(self, import_name: str) -> bool:
        """Check if an import is internal to our application."""
        return import_name.startswith("app.") or import_name.startswith("backend.")
    
    def analyze_dependencies(self):
        """Analyze all Python files in the app directory structure."""
        for root, dirs, files in os.walk(self.app_root):
            # Skip __pycache__ directories
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            
            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    filepath = Path(root) / file
                    
                    # Convert file path to module name
                    rel_path = filepath.relative_to(self.app_root.parent)
                    module_name = str(rel_path).replace(os.sep, '.').replace('.py', '')
                    
                    self.modules.add(module_name)
                    self.layer_mapping[module_name] = self.get_module_layer(module_name)
                    
                    # Extract imports
                    imports = self.extract_imports_from_file(filepath)
                    
                    # Filter to internal imports only
                    internal_imports = [imp for imp in imports if self.is_internal_import(imp)]
                    
                    self.dependencies[module_name].update(internal_imports)
    
    def check_layer_violations(self) -> List[Tuple[str, str, str]]:
        """Check for architectural layer boundary violations."""
        violations = []
        
        for module, imports in self.dependencies.items():
            module_layer = self.layer_mapping.get(module, "unknown")
            
            for imported_module in imports:
                if not self.is_internal_import(imported_module):
                    continue
                
                imported_layer = self.layer_mapping.get(imported_module, "unknown")
                
                if module_layer == "unknown" or imported_layer == "unknown":
                    continue
                
                # Check if this is a valid cross-layer dependency
                if module_layer != imported_layer:
                    # Utils can be imported by any layer
                    if imported_layer == "utils":
                        continue
                    
                    # Check if this cross-layer dependency is allowed
                    if (module_layer, imported_layer) not in self.allowed_cross_layer:
                        # Check layer hierarchy - higher layers can import from lower layers
                        module_level = self.layers.get(module_layer, 999)
                        imported_level = self.layers.get(imported_layer, 999)
                        
                        if module_level < imported_level:
                            violations.append((module, imported_module, 
                                             f"{module_layer} -> {imported_layer}"))
        
        return violations
    
    def find_circular_dependencies(self) -> List[List[str]]:
        """Find circular dependencies using DFS."""
        visited = set()
        rec_stack = set()
        cycles = []
        
        def dfs(node, path):
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in self.dependencies.get(node, []):
                if self.is_internal_import(neighbor) and neighbor in self.modules:
                    dfs(neighbor, path + [node])
            
            rec_stack.remove(node)
        
        for module in self.modules:
            if module not in visited:
                dfs(module, [])
        
        return cycles


class TestLayerBoundaryEnforcement(unittest.TestCase):
    """Property-based tests for layer boundary enforcement."""
    
    def setUp(self):
        """Set up test environment."""
        self.backend_root = Path(__file__).parent.parent
        self.app_root = self.backend_root / "app"
        self.analyzer = LayerBoundaryAnalyzer(self.app_root)
        self.analyzer.analyze_dependencies()
    
    def test_layer_boundary_enforcement_property(self):
        """
        Property 8: Layer Boundary Enforcement
        
        For any module in the refactored system, imports should only reference 
        modules from the same layer or lower layers in the architecture.
        
        **Feature: backend-refactoring, Property 8: Layer Boundary Enforcement**
        **Validates: Requirements 8.3**
        """
        violations = self.analyzer.check_layer_violations()
        
        # Report any violations found
        if violations:
            violation_messages = []
            for module, imported_module, violation_type in violations:
                violation_messages.append(
                    f"  ✗ {module} imports {imported_module} ({violation_type})"
                )
            
            self.fail(
                f"Layer boundary violations found:\n" + 
                "\n".join(violation_messages) +
                f"\n\nTotal violations: {len(violations)}"
            )
        
        # If no violations, test passes
        self.assertEqual(len(violations), 0, "No layer boundary violations should exist")
    
    def test_no_circular_dependencies_property(self):
        """
        Test that there are no circular dependencies in the module structure.
        
        **Feature: backend-refactoring, Property 8: Layer Boundary Enforcement**
        **Validates: Requirements 8.3**
        """
        cycles = self.analyzer.find_circular_dependencies()
        
        if cycles:
            cycle_messages = []
            for i, cycle in enumerate(cycles, 1):
                cycle_messages.append(f"  Cycle {i}: {' -> '.join(cycle)}")
            
            self.fail(
                f"Circular dependencies found:\n" + 
                "\n".join(cycle_messages) +
                f"\n\nTotal cycles: {len(cycles)}"
            )
        
        self.assertEqual(len(cycles), 0, "No circular dependencies should exist")
    
    def test_layer_hierarchy_consistency_property(self):
        """
        Test that the layer hierarchy is consistently maintained.
        
        **Feature: backend-refactoring, Property 8: Layer Boundary Enforcement**
        **Validates: Requirements 8.3**
        """
        # Verify that each layer only imports from same or lower layers
        layer_violations = []
        
        for module, imports in self.analyzer.dependencies.items():
            module_layer = self.analyzer.layer_mapping.get(module, "unknown")
            
            if module_layer == "unknown":
                continue
            
            module_level = self.analyzer.layers.get(module_layer, 999)
            
            for imported_module in imports:
                if not self.analyzer.is_internal_import(imported_module):
                    continue
                
                imported_layer = self.analyzer.layer_mapping.get(imported_module, "unknown")
                
                if imported_layer == "unknown":
                    continue
                
                imported_level = self.analyzer.layers.get(imported_layer, 999)
                
                # Skip if it's an allowed cross-layer dependency
                if (module_layer, imported_layer) in self.analyzer.allowed_cross_layer:
                    continue
                
                # Skip if importing from utils (allowed by any layer)
                if imported_layer == "utils":
                    continue
                
                # Skip if same layer
                if module_layer == imported_layer:
                    continue
                
                # Check if higher layer is importing from lower layer (allowed)
                if module_level > imported_level:
                    continue
                
                # This is a violation - lower layer importing from higher layer
                layer_violations.append(
                    f"{module} (layer {module_layer}, level {module_level}) "
                    f"imports {imported_module} (layer {imported_layer}, level {imported_level})"
                )
        
        if layer_violations:
            self.fail(
                f"Layer hierarchy violations found:\n" + 
                "\n".join(f"  ✗ {violation}" for violation in layer_violations)
            )
        
        self.assertEqual(len(layer_violations), 0, "Layer hierarchy should be consistent")
    
    @given(st.sampled_from(["apis", "ai", "database", "core", "utils"]))
    def test_layer_isolation_property(self, layer_name: str):
        """
        Property test: Each layer should maintain proper isolation.
        
        **Feature: backend-refactoring, Property 8: Layer Boundary Enforcement**
        **Validates: Requirements 8.3**
        """
        # Get all modules in this layer
        layer_modules = [
            module for module, layer in self.analyzer.layer_mapping.items()
            if layer == layer_name
        ]
        
        # Skip if no modules in this layer
        if not layer_modules:
            return
        
        layer_level = self.analyzer.layers.get(layer_name, 999)
        
        # Check each module in this layer
        for module in layer_modules:
            imports = self.analyzer.dependencies.get(module, set())
            
            for imported_module in imports:
                if not self.analyzer.is_internal_import(imported_module):
                    continue
                
                imported_layer = self.analyzer.layer_mapping.get(imported_module, "unknown")
                
                if imported_layer == "unknown":
                    continue
                
                imported_level = self.analyzer.layers.get(imported_layer, 999)
                
                # Allow same layer imports
                if imported_layer == layer_name:
                    continue
                
                # Allow utils imports from any layer
                if imported_layer == "utils":
                    continue
                
                # Allow explicitly permitted cross-layer dependencies
                if (layer_name, imported_layer) in self.analyzer.allowed_cross_layer:
                    continue
                
                # Allow higher layers to import from lower layers
                if layer_level > imported_level:
                    continue
                
                # This should not happen - violation of layer isolation
                self.fail(
                    f"Layer isolation violation: {module} in {layer_name} layer "
                    f"(level {layer_level}) imports {imported_module} from "
                    f"{imported_layer} layer (level {imported_level})"
                )
    
    def test_architectural_boundaries_property(self):
        """
        Test that architectural boundaries are properly maintained.
        
        **Feature: backend-refactoring, Property 8: Layer Boundary Enforcement**
        **Validates: Requirements 8.3**
        """
        # Test 1: Database layer should not import from AI or APIs
        database_modules = [
            module for module, layer in self.analyzer.layer_mapping.items()
            if layer == "database"
        ]
        
        for module in database_modules:
            imports = self.analyzer.dependencies.get(module, set())
            
            for imported_module in imports:
                if not self.analyzer.is_internal_import(imported_module):
                    continue
                
                imported_layer = self.analyzer.layer_mapping.get(imported_module, "unknown")
                
                # Database should not import from AI or APIs
                if imported_layer in ["ai", "apis"]:
                    self.fail(
                        f"Architectural boundary violation: Database module {module} "
                        f"imports from {imported_layer} layer ({imported_module})"
                    )
        
        # Test 2: Core layer should not import from AI or APIs
        core_modules = [
            module for module, layer in self.analyzer.layer_mapping.items()
            if layer == "core"
        ]
        
        for module in core_modules:
            imports = self.analyzer.dependencies.get(module, set())
            
            for imported_module in imports:
                if not self.analyzer.is_internal_import(imported_module):
                    continue
                
                imported_layer = self.analyzer.layer_mapping.get(imported_module, "unknown")
                
                # Core should not import from AI or APIs
                if imported_layer in ["ai", "apis"]:
                    self.fail(
                        f"Architectural boundary violation: Core module {module} "
                        f"imports from {imported_layer} layer ({imported_module})"
                    )
        
        # Test 3: AI layer should not import from APIs
        ai_modules = [
            module for module, layer in self.analyzer.layer_mapping.items()
            if layer == "ai"
        ]
        
        for module in ai_modules:
            imports = self.analyzer.dependencies.get(module, set())
            
            for imported_module in imports:
                if not self.analyzer.is_internal_import(imported_module):
                    continue
                
                imported_layer = self.analyzer.layer_mapping.get(imported_module, "unknown")
                
                # AI should not import from APIs
                if imported_layer == "apis":
                    self.fail(
                        f"Architectural boundary violation: AI module {module} "
                        f"imports from APIs layer ({imported_module})"
                    )
    
    def test_dependency_direction_property(self):
        """
        Test that dependencies flow in the correct direction (top-down).
        
        **Feature: backend-refactoring, Property 8: Layer Boundary Enforcement**
        **Validates: Requirements 8.3**
        """
        # Dependencies should generally flow from higher layers to lower layers
        # APIs (4) -> AI (3) -> Core/Utils (2) -> Database (1)
        
        direction_violations = []
        
        for module, imports in self.analyzer.dependencies.items():
            module_layer = self.analyzer.layer_mapping.get(module, "unknown")
            
            if module_layer == "unknown":
                continue
            
            module_level = self.analyzer.layers.get(module_layer, 999)
            
            for imported_module in imports:
                if not self.analyzer.is_internal_import(imported_module):
                    continue
                
                imported_layer = self.analyzer.layer_mapping.get(imported_module, "unknown")
                
                if imported_layer == "unknown":
                    continue
                
                imported_level = self.analyzer.layers.get(imported_layer, 999)
                
                # Skip same layer dependencies
                if module_layer == imported_layer:
                    continue
                
                # Skip utils (can be imported by any layer)
                if imported_layer == "utils":
                    continue
                
                # Skip explicitly allowed cross-layer dependencies
                if (module_layer, imported_layer) in self.analyzer.allowed_cross_layer:
                    continue
                
                # Check for upward dependencies (violations)
                if module_level < imported_level:
                    direction_violations.append(
                        f"{module} ({module_layer}, level {module_level}) -> "
                        f"{imported_module} ({imported_layer}, level {imported_level})"
                    )
        
        if direction_violations:
            self.fail(
                f"Dependency direction violations found:\n" + 
                "\n".join(f"  ✗ {violation}" for violation in direction_violations) +
                f"\n\nTotal violations: {len(direction_violations)}"
            )
        
        self.assertEqual(len(direction_violations), 0, 
                        "Dependencies should flow from higher to lower layers")


if __name__ == '__main__':
    unittest.main()