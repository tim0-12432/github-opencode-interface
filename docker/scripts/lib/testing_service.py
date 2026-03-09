'''Service for detecting and running test commands.'''

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TestingService:
    '''Detect test frameworks and execute tests in a working directory.'''

    work_dir: Path

    def detect_test_command(self) -> str | None:
        '''Detect the appropriate test command for the repository.

        Returns:
            Test command string if detected, otherwise None.
        '''
        package_json = self.work_dir / 'package.json'
        if package_json.exists():
            try:
                data = json.loads(package_json.read_text(encoding='utf-8'))
                scripts = data.get('scripts', {})
                if isinstance(scripts, dict) and 'test' in scripts:
                    return 'npm test'
            except (OSError, json.JSONDecodeError):
                pass

        if (
            (self.work_dir / 'pyproject.toml').exists()
            or (self.work_dir / 'pytest.ini').exists()
            or (self.work_dir / 'tests').is_dir()
        ):
            return 'pytest'

        if (self.work_dir / 'go.mod').exists():
            return 'go test ./...'

        if (self.work_dir / 'Cargo.toml').exists():
            return 'cargo test'

        makefile = self.work_dir / 'Makefile'
        if makefile.exists():
            try:
                contents = makefile.read_text(encoding='utf-8')
                if re.search(r'^test:', contents, re.MULTILINE):
                    return 'make test'
            except OSError:
                pass

        return None

    def run_tests(self) -> tuple[bool, str]:
        '''Run detected tests and capture output.

        Returns:
            Tuple of success flag and combined stdout/stderr output.
        '''
        command = self.detect_test_command()
        if command is None:
            return True, 'No test framework detected'

        cmd_parts = command.split()
        result = subprocess.run(
            cmd_parts,
            capture_output=True,
            text=True,
            cwd=str(self.work_dir),
            shell=False,
        )
        output = f'{result.stdout}{result.stderr}'
        return result.returncode == 0, output
