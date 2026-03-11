'''Service for detecting and installing project dependencies.'''

from __future__ import annotations

import json
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class InstallResult:
    '''Result of a single dependency installation attempt.'''

    ecosystem: str
    command: str
    success: bool
    output: str
    duration_seconds: float
    skipped: bool = False


@dataclass
class DependencyService:
    '''Detect project ecosystems and install their dependencies.'''

    work_dir: Path

    def detect_ecosystems(self) -> list[str]:
        '''Return a list of detected ecosystem identifiers.'''
        ecosystems: list[str] = []
        if (
            (self.work_dir / 'requirements.txt').exists()
            or (self.work_dir / 'pyproject.toml').exists()
            or (self.work_dir / 'setup.py').exists()
        ):
            ecosystems.append('python')
        if (self.work_dir / 'package.json').exists():
            ecosystems.append('node')
        if (self.work_dir / 'go.mod').exists():
            ecosystems.append('go')
        if (self.work_dir / 'Cargo.toml').exists():
            ecosystems.append('rust')
        if (self.work_dir / 'Gemfile').exists():
            ecosystems.append('ruby')
        return ecosystems

    def install_all(self) -> list[InstallResult]:
        '''Detect and install dependencies for all detected ecosystems.'''
        results: list[InstallResult] = []
        ecosystems = self.detect_ecosystems()
        installers = {
            'python': self._install_python,
            'node': self._install_node,
            'go': self._install_go,
            'rust': self._install_rust,
            'ruby': self._install_ruby,
        }
        for ecosystem in ecosystems:
            installer = installers.get(ecosystem)
            if installer:
                results.append(installer())
        return results

    def _install_python(self) -> InstallResult:
        '''Install Python dependencies.'''
        if not shutil.which('pip3'):
            return InstallResult(
                ecosystem='python',
                command='pip3',
                success=True,
                output='pip3 not available, skipped',
                duration_seconds=0.0,
                skipped=True,
            )
        if (self.work_dir / 'requirements.txt').exists():
            cmd = ['pip3', 'install', '-r', 'requirements.txt']
            success, output, duration = self._run_command(cmd, self.work_dir)
            return InstallResult(
                ecosystem='python',
                command=' '.join(cmd),
                success=success,
                output=output,
                duration_seconds=duration,
            )
        if (self.work_dir / 'pyproject.toml').exists():
            cmd = ['pip3', 'install', '-e', '.[dev]']
            success, output, duration = self._run_command(cmd, self.work_dir)
            if not success:
                cmd_fallback = ['pip3', 'install', '-e', '.']
                success2, output2, duration2 = self._run_command(cmd_fallback, self.work_dir)
                output = f'[dev install failed]\n{output}\n\n[fallback install]\n{output2}'
                duration += duration2
                success = success2
                cmd = cmd_fallback
            return InstallResult(
                ecosystem='python',
                command=' '.join(cmd),
                success=success,
                output=output,
                duration_seconds=duration,
            )
        if (self.work_dir / 'setup.py').exists():
            cmd = ['pip3', 'install', '-e', '.']
            success, output, duration = self._run_command(cmd, self.work_dir)
            return InstallResult(
                ecosystem='python',
                command=' '.join(cmd),
                success=success,
                output=output,
                duration_seconds=duration,
            )
        return InstallResult(
            ecosystem='python',
            command='',
            success=True,
            output='No Python install manifest found, skipped',
            duration_seconds=0.0,
            skipped=True,
        )

    def _install_node(self) -> InstallResult:
        '''Install Node.js dependencies.'''
        if not shutil.which('npm'):
            return InstallResult(
                ecosystem='node',
                command='npm',
                success=True,
                output='npm not available, skipped',
                duration_seconds=0.0,
                skipped=True,
            )
        if (self.work_dir / 'package-lock.json').exists():
            cmd = ['npm', 'ci', '--legacy-peer-deps']
        else:
            cmd = ['npm', 'install', '--legacy-peer-deps']
        success, output, duration = self._run_command(cmd, self.work_dir)
        result = InstallResult(
            ecosystem='node',
            command=' '.join(cmd),
            success=success,
            output=output,
            duration_seconds=duration,
        )
        if success and self._needs_playwright():
            pw_cmd = ['npx', 'playwright', 'install', '--with-deps']
            pw_success, pw_output, pw_duration = self._run_command(pw_cmd, self.work_dir)
            result.output += f'\n\n[playwright]\n{pw_output}'
            result.duration_seconds += pw_duration
            if not pw_success:
                result.success = False
        return result

    def _needs_playwright(self) -> bool:
        '''Check if Playwright is a dependency in package.json.'''
        package_json = self.work_dir / 'package.json'
        playwright_config = self.work_dir / 'playwright.config.ts'
        try:
            data = json.loads(package_json.read_text(encoding='utf-8'))
            all_deps = {
                **data.get('dependencies', {}),
                **data.get('devDependencies', {}),
            }
            return 'playwright' in all_deps or '@playwright/test' in all_deps or playwright_config.exists()
        except (OSError, json.JSONDecodeError):
            return False

    def _install_go(self) -> InstallResult:
        '''Install Go dependencies.'''
        if not shutil.which('go'):
            return InstallResult(
                ecosystem='go',
                command='go',
                success=True,
                output='go not available, skipped',
                duration_seconds=0.0,
                skipped=True,
            )
        cmd = ['go', 'mod', 'download']
        success, output, duration = self._run_command(cmd, self.work_dir)
        return InstallResult(
            ecosystem='go',
            command=' '.join(cmd),
            success=success,
            output=output,
            duration_seconds=duration,
        )

    def _install_rust(self) -> InstallResult:
        '''Install Rust dependencies.'''
        if not shutil.which('cargo'):
            return InstallResult(
                ecosystem='rust',
                command='cargo',
                success=True,
                output='cargo not available, skipped',
                duration_seconds=0.0,
                skipped=True,
            )
        cmd = ['cargo', 'fetch']
        success, output, duration = self._run_command(cmd, self.work_dir)
        return InstallResult(
            ecosystem='rust',
            command=' '.join(cmd),
            success=success,
            output=output,
            duration_seconds=duration,
        )

    def _install_ruby(self) -> InstallResult:
        '''Install Ruby dependencies.'''
        if not shutil.which('bundle'):
            return InstallResult(
                ecosystem='ruby',
                command='bundle',
                success=True,
                output='bundle not available, skipped',
                duration_seconds=0.0,
                skipped=True,
            )
        cmd = ['bundle', 'install']
        success, output, duration = self._run_command(cmd, self.work_dir)
        return InstallResult(
            ecosystem='ruby',
            command=' '.join(cmd),
            success=success,
            output=output,
            duration_seconds=duration,
        )

    @staticmethod
    def _run_command(
        cmd: list[str],
        cwd: Path,
        timeout: int = 300,
    ) -> tuple[bool, str, float]:
        '''Run a shell command and capture output.'''
        start = time.monotonic()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(cwd),
                shell=False,
                timeout=timeout,
            )
            output = f'{result.stdout}{result.stderr}'.strip()
            duration = time.monotonic() - start
            return result.returncode == 0, output, duration
        except subprocess.TimeoutExpired:
            duration = time.monotonic() - start
            return False, f'Command timed out after {timeout}s', duration
        except OSError as exc:
            duration = time.monotonic() - start
            return False, f'Failed to run command: {exc}', duration
