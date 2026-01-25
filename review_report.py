#!/usr/bin/env python3
"""
GitHub Repo Review CLI

Usage:
    ./review_report.py owner/repo
    ./review_report.py owner/repo --dry-run
    ./review_report.py owner/repo --verbose
    ./review_report.py owner/repo --branch existing-branch
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
                    # Handle variable references like ${GITHUB_TOKEN}
                    value = self._expand_vars(value)
                    self.values[key] = value
    
    def _expand_vars(self, value: str) -> str:
        """Expand ${VAR} references."""
        import re
        pattern = r'\$\{([^}]+)\}'
        def replace(match):
            var_name = match.group(1)
            return self.values.get(var_name, os.environ.get(var_name, ''))
        return re.sub(pattern, replace, value)
    
    def get(self, key: str, default: str = '') -> str:
        return self.values.get(key, os.environ.get(key, default))
    
    def get_env_dict(self) -> dict[str, str]:
        """Get all config values as environment variables."""
        return {k: v for k, v in self.values.items() if v}


class ReviewReporter:
    """Main resolver class."""
    
    def __init__(
        self,
        repo: str,
        config: Config,
        branch: Optional[str] = None,
        dry_run: bool = False,
        verbose: bool = False,
    ):
        self.repo = repo
        self.config = config
        self.branch = branch or "review-report"
        self.dry_run = dry_run
        self.verbose = verbose
        
        self.script_dir = Path(__file__).parent.resolve()
    
    def _log(self, msg: str) -> None:
        print(f"[resolver] {msg}")
    
    def _log_verbose(self, msg: str) -> None:
        if self.verbose:
            print(f"[resolver:debug] {msg}")
    
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
        self._log("Building Docker image...")
        
        result = subprocess.run(
            ['docker', 'build', '-t', 'github-opencode-interface', '-f', str(os.path.join(self.script_dir, 'docker', 'Dockerfile')), '.'],
            capture_output=not self.verbose,
        )
        
        return result.returncode == 0
    
    def _build_env_vars(self) -> dict[str, str]:
        """Build environment variables for the container."""
        # env = self.config.get_env_dict()

        # Add runtime values
        env = {
            'WORKFLOW_MODE': 'review',
            'REPO': self.repo,
            'BRANCH': self.branch,
            'DRY_RUN': str(self.dry_run).lower(),
            'VERBOSE': str(self.verbose).lower(),
        }
        
        return env
    
    def run(self) -> int:
        """Run the reporter."""
        
        # Validate
        if not self._check_docker():
            self._log("Error: Docker is not available")
            return 1
        
        github_token = self.config.get('GITHUB_TOKEN')
        if not github_token:
            self._log("Error: GITHUB_TOKEN not set in config.env")
            return 1
        
        # Build image
        if not self._build_docker_image():
            self._log("Error: Failed to build Docker image")
            return 1
        
        
        # Build docker command
        cmd = ['docker', 'run', '--rm', '-i']
        
        # Prepare environment
        env_vars = self._build_env_vars()
        # Add environment variables
        for key, value in env_vars.items():
            cmd.extend(['-e', f'{key}={value}'])
        
        cmd.extend(['--env-file', str(os.path.join(self.script_dir, 'config.env'))])
        
        cmd.append('github-opencode-interface')
        
        self._log_verbose(f"Running: {' '.join(cmd)}")
        
        # Print startup info
        print()
        print("=" * 60)
        print(f"  Reviewing: {self.repo}")
        print(f"  Branch:    {self.branch}")
        print(f"  Dry run:   {self.dry_run}")
        print("=" * 60)
        print()
        
        # Run container
        result = subprocess.run(cmd)
        
        # Print resume info
        if result.returncode != 0:
            print()
            print("-" * 60)
            print("  To continue working on this review, run:")
            print(f"  ./review_report.py {self.repo}")
            print("-" * 60)
            print()
        
        return result.returncode


def parse_repo(repo_str: str) -> Optional[str]:
    """Parse and validate repository string (owner/repo)."""
    pattern = r'^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$'
    if re.match(pattern, repo_str):
        return repo_str
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Automatically create a review report using AI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s owner/repo
  %(prog)s owner/repo --dry-run
  %(prog)s owner/repo --verbose
  %(prog)s owner/repo --branch fix/my-custom-branch
  %(prog)s owner/repo --config /path/to/config.env
        ''',
    )
    
    parser.add_argument(
        'repo',
        help='Repository in owner/repo format',
    )
    parser.add_argument(
        '--branch', '-b',
        help='Branch name (default: fix/review-report)',
    )
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Run without creating PR or commenting',
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output',
    )
    parser.add_argument(
        '--config', '-c',
        type=Path,
        default=Path(__file__).parent / 'config.env',
        help='Path to config file (default: config.env)',
    )
    
    args = parser.parse_args()
    
    # Validate repo format
    repo = parse_repo(args.repo)
    if not repo:
        print(f"Error: Invalid repository format: {args.repo}")
        print("Expected format: owner/repo")
        return 1
    
    # Load config
    config = Config(args.config)

    # Create and run resolver
    resolver = ReviewReporter(
        repo=repo,
        config=config,
        branch=args.branch,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )
    
    return resolver.run()


if __name__ == '__main__':
    sys.exit(main())
