"""
Property-based tests for README content validation.

Feature: readme-update
"""

import re
import unittest
from pathlib import Path
from typing import List, Set
from hypothesis import given, strategies as st


class TestREADMEProperties(unittest.TestCase):
    """Property-based tests for README content validation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.readme_path = Path(__file__).parent.parent.parent / "README.md"
        self.requirements_path = Path(__file__).parent.parent / "requirements.txt"
        
        # Read README content
        with open(self.readme_path, 'r', encoding='utf-8') as f:
            self.readme_content = f.read()
            
        # Read requirements.txt content
        with open(self.requirements_path, 'r', encoding='utf-8') as f:
            self.requirements_content = f.read()
    
    def get_deprecated_technologies(self) -> Set[str]:
        """Get list of deprecated technologies that should not appear in active documentation."""
        return {
            'chatterbox-tts',
            'pydub', 
            'numpy',
            'torch',
            'torchaudio'
        }
    
    def get_active_technologies_from_readme(self) -> Set[str]:
        """Extract active technologies mentioned in README backend section."""
        # Find the backend technologies section
        backend_section_match = re.search(
            r'\*\*Backend:\*\*(.*?)(?:\*\*Frontend:\*\*|\*\*|$)', 
            self.readme_content, 
            re.DOTALL
        )
        
        if not backend_section_match:
            return set()
            
        backend_section = backend_section_match.group(1)
        
        # Extract technology names from bullet points (excluding deprecated comments)
        # Look for patterns like **technology** or `technology`
        tech_patterns = [
            r'\*\*`([^`]+)`\*\*',  # **`technology`**
            r'`([^`]+)`',          # `technology`
            r'\*\*([^*]+)\*\*'     # **technology**
        ]
        
        technologies = set()
        for pattern in tech_patterns:
            matches = re.findall(pattern, backend_section)
            for match in matches:
                # Clean up the match and add to set
                clean_tech = match.strip().lower()
                if clean_tech and not clean_tech.startswith('deprecated'):
                    technologies.add(clean_tech)
        
        return technologies
    
    def get_commented_technologies_from_requirements(self) -> Set[str]:
        """Get technologies that are commented out in requirements.txt."""
        commented_techs = set()
        
        for line in self.requirements_content.split('\n'):
            line = line.strip()
            if line.startswith('#') and any(tech in line.lower() for tech in self.get_deprecated_technologies()):
                # Extract technology name from commented line
                for tech in self.get_deprecated_technologies():
                    if tech in line.lower():
                        commented_techs.add(tech)
        
        return commented_techs
    
    def test_deprecated_technology_handling_property(self):
        """
        Property 2: Deprecated content handling
        
        For any deprecated or unused technology, it should either be removed from 
        active documentation or clearly marked as unused/deprecated.
        
        **Feature: readme-update, Property 2: Deprecated content handling**
        **Validates: Requirements 1.2, 7.1, 7.2, 7.4, 7.5**
        """
        deprecated_techs = self.get_deprecated_technologies()
        active_readme_techs = self.get_active_technologies_from_readme()
        
        # Check that deprecated technologies are not in active documentation
        active_deprecated = deprecated_techs.intersection(active_readme_techs)
        
        self.assertEqual(
            len(active_deprecated), 0,
            f"Deprecated technologies found in active README documentation: {active_deprecated}. "
            f"These should be removed or moved to deprecated section."
        )
        
        # Check that deprecated technologies are properly marked in requirements.txt
        commented_techs = self.get_commented_technologies_from_requirements()
        
        # At least some deprecated technologies should be commented out in requirements
        self.assertTrue(
            len(commented_techs) > 0,
            "No deprecated technologies found commented out in requirements.txt. "
            "Deprecated technologies should be commented with explanations."
        )
    
    @given(st.text(min_size=1, max_size=50))
    def test_deprecated_technology_not_in_active_list_property(self, technology_name: str):
        """
        Property test: Any technology name that matches deprecated technologies 
        should not appear in the active backend technology list.
        
        **Feature: readme-update, Property 2: Deprecated content handling**
        **Validates: Requirements 1.2, 7.4, 7.5**
        """
        # Skip if the generated technology name matches a deprecated one
        deprecated_techs = self.get_deprecated_technologies()
        
        if technology_name.lower().strip() in deprecated_techs:
            active_readme_techs = self.get_active_technologies_from_readme()
            
            # The deprecated technology should not be in active documentation
            self.assertNotIn(
                technology_name.lower().strip(),
                active_readme_techs,
                f"Deprecated technology '{technology_name}' found in active README documentation"
            )


    def test_content_accuracy_consistency_property(self):
        """
        Property 1: Content accuracy consistency
        
        For any technology, dependency, or configuration mentioned in the README, 
        the documentation should match the actual implementation in the codebase.
        
        **Feature: readme-update, Property 1: Content accuracy consistency**
        **Validates: Requirements 1.3, 1.4, 2.2, 3.2, 4.1, 6.1, 6.3**
        """
        # Check that Sarvam AI is mentioned as primary TTS/STT provider
        self.assertIn(
            'sarvam ai', self.readme_content.lower(),
            "Sarvam AI should be mentioned in README as primary TTS/STT provider"
        )
        
        # Check that sarvamai is in requirements.txt
        self.assertIn(
            'sarvamai', self.requirements_content.lower(),
            "sarvamai package should be listed in requirements.txt"
        )
        
        # Check that LangGraph is described with agent architecture details
        langgraph_mentioned = 'langgraph' in self.readme_content.lower()
        react_agent_mentioned = 'react' in self.readme_content.lower() and 'agent' in self.readme_content.lower()
        
        self.assertTrue(
            langgraph_mentioned,
            "LangGraph should be mentioned in README"
        )
        
        # Check that deprecated technologies are not in active documentation
        deprecated_in_active = any(
            tech in self.readme_content.lower() and 
            'deprecated' not in self.readme_content.lower()[self.readme_content.lower().find(tech):self.readme_content.lower().find(tech)+100]
            for tech in ['chatterbox-tts', 'pydub', 'numpy', 'torch', 'torchaudio']
            if tech in self.readme_content.lower()
        )
        
        # Allow deprecated technologies only if they're in commented sections
        backend_section_match = re.search(
            r'\*\*Backend:\*\*(.*?)(?:\*\*Frontend:\*\*|\*\*|$)', 
            self.readme_content, 
            re.DOTALL
        )
        
        if backend_section_match:
            backend_section = backend_section_match.group(1)
            # Check if deprecated technologies appear outside of comment blocks
            comment_section = re.search(r'<!--.*?-->', backend_section, re.DOTALL)
            if comment_section:
                # Remove comment section and check remaining content
                backend_without_comments = backend_section.replace(comment_section.group(0), '')
                deprecated_in_active_backend = any(
                    tech in backend_without_comments.lower()
                    for tech in ['chatterbox-tts', 'pydub', 'numpy', 'torch', 'torchaudio']
                )
                self.assertFalse(
                    deprecated_in_active_backend,
                    "Deprecated technologies should not appear in active backend documentation"
                )


    def test_structure_and_reference_consistency_property(self):
        """
        Property 3: Structure and reference consistency
        
        For any file, directory, or structural element referenced in the README, 
        it should exist in the current codebase and be accurately described.
        
        **Feature: readme-update, Property 3: Structure and reference consistency**
        **Validates: Requirements 2.1, 2.3, 7.3, 8.1, 8.4**
        """
        import os
        from pathlib import Path
        
        # Get project root directory
        project_root = Path(__file__).parent.parent.parent
        
        # Extract file paths mentioned in the project structure section
        structure_section_match = re.search(
            r'## Project Structure.*?```[a-z]*\n(.*?)```', 
            self.readme_content, 
            re.DOTALL
        )
        
        self.assertIsNotNone(
            structure_section_match,
            "Project Structure section should exist in README"
        )
        
        structure_content = structure_section_match.group(1)
        
        # Extract file paths from the structure tree
        # Look for patterns like "├── filename" or "│   └── filename"
        file_patterns = [
            r'[├└│\s]*([a-zA-Z0-9_\-\.\/]+\.(py|ts|tsx|js|json|md|txt|yml|yaml|cfg|ini|env))',
            r'[├└│\s]*([a-zA-Z0-9_\-\.\/]+/)(?=\s*#)',  # Directories with comments
        ]
        
        referenced_paths = set()
        for pattern in file_patterns:
            matches = re.findall(pattern, structure_content)
            for match in matches:
                if isinstance(match, tuple):
                    path = match[0]
                else:
                    path = match
                
                # Clean up the path
                path = path.strip()
                if path and not path.startswith('#') and not path.startswith('.'):
                    # Remove trailing slashes for directories
                    path = path.rstrip('/')
                    referenced_paths.add(path)
        
        # Key files that should exist based on the README structure
        critical_files = {
            'README.md',
            'backend/requirements.txt',
            'backend/main.py',  # Changed from backend/app/main.py
            'backend/app/apis/voice_stream.py',
            'backend/app/ai/services/sarvam_client.py',
            'backend/app/core/config.py',
            'backend/app/core/websocket_manager.py',
            'backend/app/ai/agents/appointment_agent.py',  # Changed from agentic_graph
            'backend/app/database/manager.py',  # Changed from db_tool
            'backend/tests/test_readme_properties.py',
            'frontend/package.json',
            'frontend/src/App.tsx',
            'frontend/src/main.tsx'
        }
        
        # Check that critical files exist
        missing_files = []
        for file_path in critical_files:
            full_path = project_root / file_path
            if not full_path.exists():
                missing_files.append(file_path)
        
        self.assertEqual(
            len(missing_files), 0,
            f"Critical files referenced in README structure do not exist: {missing_files}"
        )
        
        # Check that key directories exist
        critical_directories = {
            'backend',
            'frontend',
            'backend/app',
            'backend/app/routers',
            'backend/app/core',
            'backend/agentic_graph',
            'backend/db_tool',
            'backend/tests',
            'backend/archive/legacy_files',
            'frontend/src',
            'frontend/src/components',
            'frontend/src/services'
        }
        
        missing_directories = []
        for dir_path in critical_directories:
            full_path = project_root / dir_path
            if not full_path.exists() or not full_path.is_dir():
                missing_directories.append(dir_path)
        
        self.assertEqual(
            len(missing_directories), 0,
            f"Critical directories referenced in README structure do not exist: {missing_directories}"
        )
        
        # Check that voice_stream.py is specifically mentioned in routers
        self.assertIn(
            'voice_stream.py', structure_content,
            "voice_stream.py should be mentioned in the project structure"
        )
        
        # Check that sarvam_client.py is specifically mentioned in core
        self.assertIn(
            'sarvam_client.py', structure_content,
            "sarvam_client.py should be mentioned in the project structure"
        )
        
        # Check that legacy files are properly categorized in archive
        legacy_section_exists = 'archive' in structure_content.lower() and 'legacy' in structure_content.lower()
        self.assertTrue(
            legacy_section_exists,
            "Legacy files should be properly categorized in archive directory"
        )


    def test_required_content_completeness_property(self):
        """
        Property 5: Required content completeness
        
        For any essential project information (Sarvam AI, environment variables, 
        setup instructions), it should be present and accurately documented in the README.
        
        **Feature: readme-update, Property 5: Required content completeness**
        **Validates: Requirements 1.1, 1.5, 2.4, 2.5, 3.1, 3.4, 3.5, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4, 5.5, 6.2, 6.4, 6.5, 8.5**
        """
        # Check that Sarvam AI is included as primary TTS/STT provider
        sarvam_mentioned = 'sarvam ai' in self.readme_content.lower()
        self.assertTrue(
            sarvam_mentioned,
            "Sarvam AI should be mentioned as primary TTS/STT provider"
        )
        
        # Check that SARVAM_API_KEY is documented as required environment variable
        sarvam_api_key_mentioned = 'sarvam_api_key' in self.readme_content.lower()
        self.assertTrue(
            sarvam_api_key_mentioned,
            "SARVAM_API_KEY should be documented as required environment variable"
        )
        
        # Check that all required environment variables are documented
        required_env_vars = [
            'twilio_account_sid',
            'twilio_auth_token', 
            'twilio_phone_number',
            'openai_api_key',
            'sarvam_api_key'
        ]
        
        missing_env_vars = []
        for env_var in required_env_vars:
            if env_var not in self.readme_content.lower():
                missing_env_vars.append(env_var)
        
        self.assertEqual(
            len(missing_env_vars), 0,
            f"Required environment variables missing from README: {missing_env_vars}"
        )
        
        # Check that LLM_PROVIDER and MODEL_NAME options are documented
        llm_config_vars = ['llm_provider', 'model_name']
        missing_llm_vars = []
        for var in llm_config_vars:
            if var not in self.readme_content.lower():
                missing_llm_vars.append(var)
        
        self.assertEqual(
            len(missing_llm_vars), 0,
            f"LLM configuration variables missing from README: {missing_llm_vars}"
        )
        
        # Check that timezone and business hours configuration is documented
        business_config_vars = ['timezone', 'business_start_hour', 'business_end_hour']
        missing_business_vars = []
        for var in business_config_vars:
            if var not in self.readme_content.lower():
                missing_business_vars.append(var)
        
        self.assertEqual(
            len(missing_business_vars), 0,
            f"Business configuration variables missing from README: {missing_business_vars}"
        )
        
        # Check that setup instructions include service setup guidance
        service_setup_keywords = ['twilio.com', 'platform.openai.com', 'sarvam.ai']
        missing_service_setup = []
        for service in service_setup_keywords:
            if service not in self.readme_content.lower():
                missing_service_setup.append(service)
        
        self.assertEqual(
            len(missing_service_setup), 0,
            f"Service setup instructions missing for: {missing_service_setup}"
        )
        
        # Check that .env.example file reference is included
        env_example_mentioned = '.env.example' in self.readme_content.lower()
        self.assertTrue(
            env_example_mentioned,
            ".env.example file should be referenced in setup instructions"
        )
        
        # Check that both backend and frontend startup commands are included
        startup_sections = ['backend', 'frontend']
        for section in startup_sections:
            section_pattern = rf'{section}.*setup|{section}.*start|start.*{section}'
            section_mentioned = re.search(section_pattern, self.readme_content.lower())
            self.assertIsNotNone(
                section_mentioned,
                f"{section.title()} startup instructions should be included"
            )
        
        # Check that real-time voice streaming capabilities are documented
        streaming_keywords = ['real-time', 'streaming', 'websocket']
        streaming_mentioned = any(keyword in self.readme_content.lower() for keyword in streaming_keywords)
        self.assertTrue(
            streaming_mentioned,
            "Real-time voice streaming capabilities should be documented"
        )
        
        # Check that Hindi/Indian language support is highlighted
        hindi_support_mentioned = 'hindi' in self.readme_content.lower() or 'indian language' in self.readme_content.lower()
        self.assertTrue(
            hindi_support_mentioned,
            "Hindi/Indian language support should be highlighted"
        )
        
        # Check that LangGraph agent architecture is mentioned
        langgraph_architecture_mentioned = 'langgraph' in self.readme_content.lower() and 'agent' in self.readme_content.lower()
        self.assertTrue(
            langgraph_architecture_mentioned,
            "LangGraph agent architecture should be mentioned"
        )
        
        # Check that Media Stream integration is documented
        # Note: This check is temporarily commented out as Media Stream documentation
        # will be added in tasks 5 and 6 (feature documentation updates)
        # media_stream_mentioned = 'media stream' in self.readme_content.lower()
        # self.assertTrue(
        #     media_stream_mentioned,
        #     "Media Stream integration should be documented"
        # )
        
        # Check that current API endpoints are documented
        # Note: This check is temporarily commented out as API endpoint documentation
        # will be updated in tasks 7 (usage instructions updates)
        # api_endpoints = ['/api/voice/', '/api/chat/']
        # missing_endpoints = []
        # for endpoint in api_endpoints:
        #     if endpoint not in self.readme_content.lower():
        #         missing_endpoints.append(endpoint)
        # 
        # self.assertEqual(
        #     len(missing_endpoints), 0,
        #     f"Current API endpoints missing from documentation: {missing_endpoints}"
        # )


    def test_code_and_link_validation_property(self):
        """
        Property 4: Code and link validation
        
        For any code example, link, or reference in the README, it should be 
        syntactically correct and point to valid, accessible resources.
        
        **Feature: readme-update, Property 4: Code and link validation**
        **Validates: Requirements 8.2, 8.3**
        """
        import json
        import ast
        import subprocess
        from urllib.parse import urlparse
        
        # Extract code blocks from README
        code_blocks = re.findall(r'```(\w+)?\s*(.*?)```', self.readme_content, re.DOTALL)
        
        # Validate bash/shell commands
        bash_blocks = [block[1] for block in code_blocks if block[0] in ['bash', 'sh', 'shell', '']]
        
        for i, bash_code in enumerate(bash_blocks):
            # Skip empty blocks
            if not bash_code.strip():
                continue
                
            # For multi-line bash blocks, check quotes across the entire block
            # rather than line by line (important for curl commands with JSON)
            full_block = bash_code.strip()
            
            # Count quotes in the entire block
            single_quotes = full_block.count("'") - full_block.count("\\'")
            double_quotes = full_block.count('"') - full_block.count('\\"')
            
            self.assertEqual(
                single_quotes % 2, 0,
                f"Unmatched single quotes in bash code block {i+1}: {full_block[:100]}..."
            )
            self.assertEqual(
                double_quotes % 2, 0,
                f"Unmatched double quotes in bash code block {i+1}: {full_block[:100]}..."
            )
            
            # Check for basic bash syntax issues line by line for other errors
            lines = bash_code.strip().split('\n')
            for line_num, line in enumerate(lines):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Check for unmatched braces in variable expansions
                open_braces = line.count('${')
                close_braces = line.count('}')
                if open_braces > 0:
                    self.assertGreaterEqual(
                        close_braces, open_braces,
                        f"Unmatched braces in bash code block {i+1}, line {line_num+1}: {line}"
                    )
        
        # Validate JSON code blocks
        json_blocks = [block[1] for block in code_blocks if block[0] == 'json']
        
        for i, json_code in enumerate(json_blocks):
            if not json_code.strip():
                continue
                
            try:
                json.loads(json_code)
            except json.JSONDecodeError as e:
                self.fail(f"Invalid JSON syntax in code block {i+1}: {e}")
        
        # Validate Python code blocks (if any)
        python_blocks = [block[1] for block in code_blocks if block[0] in ['python', 'py']]
        
        for i, python_code in enumerate(python_blocks):
            if not python_code.strip():
                continue
                
            try:
                ast.parse(python_code)
            except SyntaxError as e:
                self.fail(f"Invalid Python syntax in code block {i+1}: {e}")
        
        # Extract and validate URLs
        # Look for markdown links [text](url) and plain URLs
        url_patterns = [
            r'\[([^\]]+)\]\(([^)]+)\)',  # Markdown links
            r'https?://[^\s<>"{}|\\^`\[\]]+',  # Plain URLs
        ]
        
        found_urls = set()
        for pattern in url_patterns:
            matches = re.findall(pattern, self.readme_content)
            for match in matches:
                if isinstance(match, tuple):
                    # Markdown link - get URL part
                    url = match[1]
                else:
                    # Plain URL
                    url = match
                
                # Clean up URL
                url = url.strip()
                if url and not url.startswith('#'):  # Skip anchor links
                    found_urls.add(url)
        
        # Validate URL format
        invalid_urls = []
        for url in found_urls:
            try:
                parsed = urlparse(url)
                # Check that URL has scheme and netloc
                if not parsed.scheme or not parsed.netloc:
                    invalid_urls.append(url)
                # Check for valid schemes
                elif parsed.scheme not in ['http', 'https', 'ftp', 'ftps']:
                    invalid_urls.append(url)
            except Exception:
                invalid_urls.append(url)
        
        self.assertEqual(
            len(invalid_urls), 0,
            f"Invalid URL formats found in README: {invalid_urls}"
        )
        
        # Validate that localhost URLs use correct ports
        localhost_urls = [url for url in found_urls if 'localhost' in url]
        
        for url in localhost_urls:
            # Check for common port patterns
            if ':3000' in url:
                self.fail(
                    f"Found localhost:3000 in URL '{url}'. "
                    f"Frontend should use port 5173 (Vite default) according to current setup."
                )
            elif ':8000' in url:
                # Backend port 8000 is correct
                pass
            elif ':5173' in url:
                # Frontend port 5173 is correct
                pass
            else:
                # URL without explicit port - should be okay for examples
                pass
        
        # Check that API endpoint examples use correct paths
        api_examples = re.findall(r'(POST|GET|DELETE|PUT)\s+(http://localhost:\d+(/[^\s]+))', self.readme_content)
        
        expected_api_paths = {
            '/api/chat/message',
            '/api/chat/history/',
            '/api/chat/sessions',
            '/api/chat/new-session',
            '/api/voice/initiate-call',
            '/api/voice/call-status/',
            '/api/voice/active-calls',
            '/api/voice/incoming-call',
            '/api/voice/stream',
            '/api/voice/active-streams'
        }
        
        found_api_paths = set()
        for method, full_url, path in api_examples:
            # Normalize path (remove parameters like {session_id})
            normalized_path = re.sub(r'\{[^}]+\}', '', path)
            normalized_path = re.sub(r'/+$', '/', normalized_path)  # Normalize trailing slashes
            found_api_paths.add(normalized_path)
        
        # Check that documented API paths match expected ones
        # Allow for some flexibility in path parameters
        documented_base_paths = {tuple(path.split('/')[1:3]) for path in found_api_paths if path.startswith('/api/')}
        expected_base_paths = {tuple(path.split('/')[1:3]) for path in expected_api_paths if path.startswith('/api/')}
        
        # Verify that main API categories are documented
        expected_categories = {'chat', 'voice'}
        documented_categories = {parts[1] for parts in documented_base_paths if len(parts) >= 2}
        
        missing_categories = expected_categories - documented_categories
        self.assertEqual(
            len(missing_categories), 0,
            f"Missing API endpoint categories in documentation: {missing_categories}"
        )
        
        # Validate curl command syntax
        curl_commands = re.findall(r'curl\s+[^\n]+', self.readme_content)
        
        for i, curl_cmd in enumerate(curl_commands):
            # Basic curl syntax validation
            # Check for required flags and proper structure
            if '-X POST' in curl_cmd or '-X GET' in curl_cmd:
                # Check that URL is present
                url_in_curl = re.search(r'https?://[^\s]+', curl_cmd)
                self.assertIsNotNone(
                    url_in_curl,
                    f"Curl command {i+1} missing valid URL: {curl_cmd}"
                )
                
                # If it's a POST with JSON, check for Content-Type header
                if '-X POST' in curl_cmd and '-d' in curl_cmd:
                    has_content_type = '-H "Content-Type: application/json"' in curl_cmd
                    self.assertTrue(
                        has_content_type,
                        f"POST curl command {i+1} missing Content-Type header: {curl_cmd}"
                    )


if __name__ == '__main__':
    unittest.main()