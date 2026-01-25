#!/usr/bin/env python3
"""
suggest_issues.py - Create GitHub issues from AI-generated suggestions.

This is a standalone tool for creating improvement issues for a repository.

Usage:
    ./suggest_issues.py owner/repo
    ./suggest_issues.py owner/repo --source-issue 123
    ./suggest_issues.py owner/repo --count 5
    ./suggest_issues.py owner/repo --dry-run
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional


class Config:
    """Configuration loaded from config.env file."""

    def __init__(self, config_path: Path):
        self.values: dict[str, str] = {}
        self._load(config_path)

    def _load(self, path: Path) -> None:
        if not path.exists():
            return

        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, _, value = line.partition('=')
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    value = self._expand_vars(value)
                    self.values[key] = value

    def _expand_vars(self, value: str) -> str:
        """Expand ${VAR} references."""
        pattern = r'\$\{([^}]+)\}'

        def replace(match: re.Match[str]) -> str:
            var_name = match.group(1)
            return self.values.get(var_name, os.environ.get(var_name, ''))

        return re.sub(pattern, replace, value)

    def get(self, key: str, default: str = '') -> str:
        return self.values.get(key, os.environ.get(key, default))

    def get_env_dict(self) -> dict[str, str]:
        """Get all config values as environment variables."""
        return {k: v for k, v in self.values.items() if v}


class SuggestIssues:
    """Suggest issues CLI wrapper."""

    def __init__(
        self,
        repo: str,
        config: Config,
        source_issue: Optional[int] = None,
        count: int = 3,
        dry_run: bool = False,
        verbose: bool = False,
    ) -> None:
        self.repo = repo
        self.config = config
        self.source_issue = source_issue
        self.count = count
        self.dry_run = dry_run
        self.verbose = verbose
        self.script_dir = Path(__file__).parent.resolve()

    def _log(self, msg: str) -> None:
        print(f'[suggest] {msg}')

    def _log_verbose(self, msg: str) -> None:
        if self.verbose:
            print(f'[suggest:debug] {msg}')

    def _check_docker(self) -> bool:
        """Check if Docker is available."""
        try:
            subprocess.run(
                ['docker', 'info'],
                capture_output=True,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _build_docker_image(self) -> bool:
        """Build the Docker image if needed."""
        self._log('Building Docker image...')

        result = subprocess.run(
            [
                'docker',
                'build',
                '-t',
                'issue-resolver',
                '-f',
                str(os.path.join(self.script_dir, 'docker', 'Dockerfile')),
                '.',
            ],
            capture_output=not self.verbose,
        )

        return result.returncode == 0

    def _build_env_vars(self) -> dict[str, str]:
        """Build environment variables for the container."""
        env = self.config.get_env_dict()

        env.update(
            {
                'WORKFLOW_MODE': 'suggest',
                'REPO': self.repo,
                'SUGGESTED_ISSUES_COUNT': str(self.count),
                'DRY_RUN': str(self.dry_run).lower(),
                'VERBOSE': str(self.verbose).lower(),
            },
        )

        if self.source_issue is not None:
            env['ISSUE'] = str(self.source_issue)

        return env

    def run(self) -> int:
        """Run the suggestion generator."""
        if not self._check_docker():
            self._log('Error: Docker is not available')
            return 1

        github_token = self.config.get('GITHUB_TOKEN')
        if not github_token:
            self._log('Error: GITHUB_TOKEN not set in config.env')
            return 1

        if not self._build_docker_image():
            self._log('Error: Failed to build Docker image')
            return 1

        cmd = ['docker', 'run', '--rm', '-i']

        env_vars = self._build_env_vars()
        for key, value in env_vars.items():
            cmd.extend(['-e', f'{key}={value}'])

        cmd.extend(['--env-file', str(os.path.join(self.script_dir, 'config.env'))])
        cmd.append('issue-resolver')

        self._log_verbose(f"Running: {' '.join(cmd)}")

        print()
        print('=' * 60)
        print(f'  Repository: {self.repo}')
        if self.source_issue:
            print(f'  Source:     #{self.source_issue}')
        print(f'  Count:      {self.count}')
        print(f'  Dry run:    {self.dry_run}')
        print('=' * 60)
        print()

        result = subprocess.run(cmd)
        return result.returncode


def parse_repo(repo_str: str) -> Optional[str]:
    """Parse and validate repository string (owner/repo)."""
    pattern = r'^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$'
    if re.match(pattern, repo_str):
        return repo_str
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Create AI-generated improvement issues for a repository',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s owner/repo
  %(prog)s owner/repo --source-issue 123
  %(prog)s owner/repo --count 5
  %(prog)s owner/repo --dry-run
        ''',
    )

    parser.add_argument(
        'repo',
        help='Repository in owner/repo format',
    )
    parser.add_argument(
        '--source-issue',
        '-i',
        type=int,
        help='Source issue number (adds context to suggestions)',
    )
    parser.add_argument(
        '--count',
        '-c',
        type=int,
        default=3,
        help='Number of issues to suggest (default: 3)',
    )
    parser.add_argument(
        '--dry-run',
        '-n',
        action='store_true',
        help='Run without creating issues',
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose output',
    )
    parser.add_argument(
        '--config',
        type=Path,
        default=Path(__file__).parent / 'config.env',
        help='Path to config file (default: config.env)',
    )

    args = parser.parse_args()

    repo = parse_repo(args.repo)
    if not repo:
        print(f'Error: Invalid repository format: {args.repo}')
        print('Expected format: owner/repo')
        return 1

    if args.count <= 0:
        print('Error: --count must be greater than 0')
        return 1

    config = Config(args.config)

    suggester = SuggestIssues(
        repo=repo,
        config=config,
        source_issue=args.source_issue,
        count=args.count,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    return suggester.run()


if __name__ == '__main__':
    sys.exit(main())
