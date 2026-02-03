#!/usr/bin/env python3
"""
GitHub Issue Resolver CLI

Usage:
    ./resolve.py owner/repo 123
    ./resolve.py owner/repo 123 --dry-run
    ./resolve.py owner/repo 123 --verbose
    ./resolve.py owner/repo 123 --branch existing-branch
"""

import argparse
import os
import re
import subprocess
import sys
# pip install pyjwt
import jwt
import time
import requests
from pathlib import Path
from typing import Optional

import docker_cache

def get_auth_token(
    repo: str,
    client_id: str,
    private_key_path: str,
) -> Optional[str]:
    """Generate a GitHub App installation access token."""
    try:
        with open(private_key_path, 'r') as f:
            private_key = f.read()
        
        # Create JWT
        now = int(time.time())
        payload = {
            'iat': now - 60,
            'exp': now + (9 * 60),
            'iss': client_id,
        }
        encoded_jwt = jwt.encode(payload, private_key, algorithm='RS256')
        
        # Get installation ID
        headers = {
            'Authorization': f'Bearer {encoded_jwt}',
            'Accept': 'application/vnd.github.v3+json',
            'X-GitHub-Api-Version': '2022-11-28',
        }
        response = requests.get(f'https://api.github.com/repos/{repo}/installation', headers=headers)
        response.raise_for_status()
        access_token_url = response.json()['access_tokens_url']
        
        # Create access token
        response = requests.post(access_token_url, headers=headers)
        response.raise_for_status()
        token_data = response.json()
        return token_data['token']
    except FileNotFoundError:
        print(f"Error: Private key file not found: {private_key_path}")
        return None
    except jwt.exceptions.InvalidKeyError as e:
        print(f"Error: Invalid private key format: {e}")
        print("Ensure the key is in PEM format (begins with -----BEGIN RSA PRIVATE KEY-----)")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"Error: GitHub API request failed: {e}")
        print(f"Response: {e.response.text if e.response else 'No response'}")
        return None
    except Exception as e:
        print(f"Error generating auth token: {e}")
        return None


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


class Resolver:
    """Main resolver class."""
    
    def __init__(
        self,
        repo: str,
        issue: int,
        config: Config,
        branch: Optional[str] = None,
        dry_run: bool = False,
        verbose: bool = False,
        force_build: bool = False,
    ):
        self.repo = repo
        self.issue = issue
        self.config = config
        self.branch = branch or f"fix/issue-{issue}"
        self.dry_run = dry_run
        self.verbose = verbose
        self.force_build = force_build
        
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
        dockerfile_path = str(os.path.join(self.script_dir, 'docker', 'Dockerfile'))
        image_name = 'github-opencode-interface'
        should_rebuild, content_hash = docker_cache.should_rebuild_image(
            repo_root=str(self.script_dir),
            image_name=image_name,
            force_build=self.force_build,
        )

        if not should_rebuild:
            self._log(f"Docker cache hit (hash={content_hash}). Using existing image.")
            return True

        self._log(f"Docker cache miss (hash={content_hash}). Building image...")
        return docker_cache.build_docker_image(
            dockerfile_path=dockerfile_path,
            image_name=image_name,
            content_hash=content_hash,
            verbose=self.verbose,
        )
    
    def _build_env_vars(self) -> dict[str, str]:
        """Build environment variables for the container."""
        #env = self.config.get_env_dict()

        # Add runtime values
        env = {
            'WORKFLOW_MODE': 'resolve',
            'REPO': self.repo,
            'ISSUE': str(self.issue),
            'BRANCH': self.branch,
            'DRY_RUN': str(self.dry_run).lower(),
            'VERBOSE': str(self.verbose).lower(),
            'SUGGESTED_ISSUES_COUNT': self.config.get('SUGGESTED_ISSUES_COUNT', '3'),
        }
        
        return env
    
    def run(self) -> int:
        """Run the resolver."""
        
        # Validate
        if not self._check_docker():
            self._log("Error: Docker is not available")
            return 1
        
        github_token = self.config.get('GITHUB_TOKEN')
        github_client_id = self.config.get('GITHUB_CLIENT_ID')
        github_private_key = self.config.get('GITHUB_PRIVATE_KEY')

        token_auth_set = bool(github_token)
        app_auth_set = bool(github_client_id and github_private_key)

        if not (token_auth_set or app_auth_set):
            self._log("Error: Either GITHUB_TOKEN or all of GITHUB_CLIENT_ID, and GITHUB_PRIVATE_KEY must be set in config.env")
            return 1
        
        # Build image
        if not self._build_docker_image():
            self._log("Error: Failed to build Docker image")
            return 1
        
        # Build docker command
        cmd = ['docker', 'run', '--rm', '-i']
        
        # Prepare environment
        env_vars = self._build_env_vars()
        if app_auth_set:
            token = get_auth_token(
                self.repo,
                github_client_id,
                github_private_key,
            )
            if not token:
                self._log("Error: Failed to obtain GitHub authentication token")
                return 1
            env_vars['GITHUB_TOKEN'] = token
        if not env_vars.get('GITHUB_TOKEN'):
            self._log("Error: Failed to obtain GitHub authentication token")
            return 1

        # Add environment variables
        for key, value in env_vars.items():
            cmd.extend(['-e', f'{key}={value}'])
        
        cmd.extend(['--env-file', str(os.path.join(self.script_dir, 'config.env'))])
        
        cmd.append('github-opencode-interface')
        
        self._log_verbose(f"Running: {' '.join(cmd)}")
        
        # Print startup info
        print()
        print("=" * 60)
        print(f"  Resolving: {self.repo}#{self.issue}")
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
            print("  To continue working on this issue, run:")
            print(f"  ./resolve.py {self.repo} {self.issue}")
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
        description='Automatically resolve GitHub issues using AI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s owner/repo 123
  %(prog)s owner/repo 123 --dry-run
  %(prog)s owner/repo 123 --verbose
  %(prog)s owner/repo 123 --branch fix/my-custom-branch
  %(prog)s owner/repo 123 --config /path/to/config.env
        ''',
    )
    
    parser.add_argument(
        'repo',
        help='Repository in owner/repo format',
    )
    parser.add_argument(
        'issue',
        type=int,
        help='Issue number',
    )
    parser.add_argument(
        '--branch', '-b',
        help='Branch name (default: fix/issue-<number>)',
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
    parser.add_argument(
        '--force-build',
        action='store_true',
        help='Force rebuilding the Docker image',
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
    resolver = Resolver(
        repo=repo,
        issue=args.issue,
        config=config,
        branch=args.branch,
        dry_run=args.dry_run,
        verbose=args.verbose,
        force_build=args.force_build,
    )
    
    return resolver.run()


if __name__ == '__main__':
    sys.exit(main())
