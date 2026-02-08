"""Script generation system for MiniClaw agent to create Python scripts for structured tasks."""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional

from .util import LOGGER


class ScriptGenerator:
    """Generate and manage Python scripts for structured tasks."""

    def __init__(self, workspace_dir: Path) -> None:
        self.scripts_dir = workspace_dir / "generated_scripts"
        self.scripts_dir.mkdir(parents=True, exist_ok=True)
        self.script_registry: Dict[str, Dict[str, Any]] = {}

    def generate_script_hash(self, code: str) -> str:
        """Generate a hash for the script content to detect changes."""
        return hashlib.sha256(code.encode('utf-8')).hexdigest()[:16]

    def validate_python_syntax(self, code: str) -> bool:
        """Validate Python syntax of generated code."""
        try:
            ast.parse(code)
            return True
        except SyntaxError as e:
            LOGGER.error(f"Generated script has syntax error: {e}")
            return False

    def save_script(self, name: str, code: str, description: str = "") -> Dict[str, Any]:
        """Save a generated script to disk and register it."""
        if not self.validate_python_syntax(code):
            raise ValueError("Generated script has invalid Python syntax")

        script_hash = self.generate_script_hash(code)
        filename = f"{name}_{script_hash}.py"
        script_path = self.scripts_dir / filename

        # Write the script
        script_path.write_text(code, encoding='utf-8')

        # Register the script
        script_info = {
            "name": name,
            "path": str(script_path),
            "hash": script_hash,
            "description": description,
            "created_at": self._get_current_timestamp(),
        }

        self.script_registry[name] = script_info
        LOGGER.info(f"Saved generated script: {name} -> {script_path}")

        return script_info

    def get_script_path(self, name: str) -> Optional[str]:
        """Get the path to a generated script."""
        script_info = self.script_registry.get(name)
        if not script_info:
            return None

        script_path = Path(script_info["path"])
        if script_path.exists():
            return str(script_path)
        return None

    def list_scripts(self) -> List[Dict[str, Any]]:
        """List all registered scripts."""
        return list(self.script_registry.values())

    def delete_script(self, name: str) -> bool:
        """Delete a generated script."""
        script_info = self.script_registry.get(name)
        if not script_info:
            return False

        script_path = Path(script_info["path"])
        if script_path.exists():
            script_path.unlink()

        del self.script_registry[name]
        LOGGER.info(f"Deleted generated script: {name}")
        return True

    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from .util import utc_now
        return utc_now()

    def generate_structured_task_script(
        self,
        task_name: str,
        task_description: str,
        parameters: List[Dict[str, Any]],
        result_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a Python script for a structured task."""

        # Generate parameter definitions
        param_defs = []
        param_docstrings = []
        param_assignments = []

        for param in parameters:
            param_name = param["name"]
            param_type = param.get("type", "str")
            param_desc = param.get("description", "")
            param_required = param.get("required", True)
            param_default = param.get("default", None)

            # Add to docstring
            required_str = " (required)" if param_required else " (optional)"
            param_docstrings.append(f"        {param_name} ({param_type}): {param_desc}{required_str}")

            # Add parameter assignment with validation
            if param_required:
                param_assignments.append(f"    if '{param_name}' not in kwargs:")
                param_assignments.append(f"        raise ValueError('Missing required parameter: {param_name}')")
                param_assignments.append(f"    {param_name} = kwargs['{param_name}']")
            else:
                default_val = repr(param_default) if param_default is not None else "None"
                param_assignments.append(f"    {param_name} = kwargs.get('{param_name}', {default_val})")

            param_defs.append(f"{param_name}: {param_type}")

        # Generate the script template
        script_template = f'''"""Auto-generated script for task: {task_name}

{task_description}

Parameters:
{chr(10).join(param_docstrings) if param_docstrings else '    None'}

Returns:
    dict: Result matching schema {result_schema}
"""

import json
import sys
from typing import Any, Dict


def execute_task(**kwargs) -> Dict[str, Any]:
    """Execute the structured task with the provided parameters."""

    # Parameter validation and extraction
{chr(10).join(param_assignments) if param_assignments else '    pass'}

    # TODO: Implement the actual task logic here
    # This is where you would implement the specific functionality
    # based on the task requirements

    # Example implementation (replace with actual logic):
    result = {{
        "task_name": "{task_name}",
        "status": "completed",
        "output": "Task executed successfully",
        "parameters_received": kwargs
    }}

    return result


def main():
    """Main entry point for the script."""
    try:
        # Read input from stdin (JSON)
        input_data = json.load(sys.stdin)

        # Execute the task
        result = execute_task(**input_data)

        # Output result as JSON
        json.dump(result, sys.stdout)

    except Exception as e:
        error_result = {{
            "task_name": "{task_name}",
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }}
        json.dump(error_result, sys.stdout)
        sys.exit(1)


if __name__ == "__main__":
    main()
'''

        # Save the script
        return self.save_script(
            name=task_name,
            code=script_template,
            description=task_description
        )

    def execute_script(self, name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a generated script with the provided parameters."""
        import json
        import subprocess
        import sys

        script_path = self.get_script_path(name)
        if not script_path:
            raise ValueError(f"Script not found: {name}")

        try:
            # Execute the script with parameters as JSON input
            result = subprocess.run(
                [sys.executable, script_path],
                input=json.dumps(parameters),
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode != 0:
                raise RuntimeError(f"Script execution failed: {result.stderr}")

            # Parse the output
            output_data = json.loads(result.stdout)
            return output_data

        except subprocess.TimeoutExpired:
            raise RuntimeError("Script execution timed out")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Script output is not valid JSON: {e}")
        except Exception as e:
            raise RuntimeError(f"Script execution error: {e}")
