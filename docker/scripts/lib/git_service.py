from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Optional

from .exceptions import GitError


_UNSET: object = object()


class GitService:
    """Provides git operations scoped to a working directory."""

    def __init__(self, work_dir: Path, token: str) -> None:
        """Initialize the git service.

        Args:
            work_dir: Path to the repository working directory.
            token: GitHub token used for authenticated clone URLs.
        """
        self.work_dir = work_dir
        self.token = token

    def configure_identity(self, name: str, email: str) -> None:
        """Configure git user name and email for the repository.

        Args:
            name: Git user name.
            email: Git user email.
        """
        try:
            # Use cwd=None: --global config writes to ~/.gitconfig and does not
            # require a specific working directory. This also ensures the method
            # works before the repository has been cloned.
            self._run('git', 'config', '--global', 'user.email', email, cwd=None)
            self._run('git', 'config', '--global', 'user.name', name, cwd=None)
        except subprocess.CalledProcessError as exc:
            raise GitError(f'Failed to configure git identity: {exc.stdout}') from exc

    def clone(self, repo: str, depth: int = 100) -> None:
        """Clone a repository into the working directory.

        Args:
            repo: Repository in the form owner/name.
            depth: Clone depth for shallow clones.
        """
        try:
            if self.work_dir.exists():
                shutil.rmtree(self.work_dir)
            self.work_dir.mkdir(parents=True, exist_ok=True)

            clone_url = f'https://x-access-token:{self.token}@github.com/{repo}.git'
            self._run('git', 'clone', '--depth', str(depth), clone_url, '.', cwd=self.work_dir)
        except (OSError, subprocess.CalledProcessError) as exc:
            raise GitError(f'Failed to clone repository {repo}: {exc}') from exc

    def get_default_branch(self) -> str:
        """Return the default branch name for the origin remote.

        Returns:
            Default branch name.
        """
        try:
            result = self._run('git', 'symbolic-ref', 'refs/remotes/origin/HEAD')
            ref = result.stdout.strip()
            if not ref:
                raise GitError('Default branch reference is empty')
            return ref.replace('refs/remotes/origin/', '', 1)
        except subprocess.CalledProcessError as exc:
            raise GitError(f'Failed to get default branch: {exc.stdout}') from exc

    def branch_exists_remote(self, branch: str) -> bool:
        """Check whether a branch exists on the remote.

        Args:
            branch: Branch name to check.

        Returns:
            True if the branch exists on origin, otherwise False.
        """
        try:
            result = self._run('git', 'ls-remote', '--heads', 'origin', branch)
            return bool(result.stdout.strip())
        except subprocess.CalledProcessError as exc:
            raise GitError(f'Failed to check remote branch {branch}: {exc.stdout}') from exc

    def checkout_new(self, branch: str) -> None:
        """Create and checkout a new branch.

        Args:
            branch: Branch name to create.
        """
        try:
            self._run('git', 'checkout', '-b', branch)
        except subprocess.CalledProcessError as exc:
            raise GitError(f'Failed to create branch {branch}: {exc.stdout}') from exc

    def checkout_existing(self, branch: str) -> None:
        """Fetch and checkout an existing branch.

        Args:
            branch: Branch name to checkout.
        """
        try:
            self._run('git', 'fetch', 'origin', f'{branch}:{branch}')
            self._run('git', 'checkout', branch)
        except subprocess.CalledProcessError as exc:
            raise GitError(f'Failed to checkout branch {branch}: {exc.stdout}') from exc

    def has_changes(self) -> bool:
        """Check for uncommitted changes.

        Returns:
            True if there are uncommitted changes.
        """
        try:
            result = self._run('git', 'status', '--porcelain')
            return bool(result.stdout.strip())
        except subprocess.CalledProcessError as exc:
            raise GitError(f'Failed to check git status: {exc.stdout}') from exc

    def add_all(self) -> None:
        """Stage all changes in the repository."""
        try:
            self._run('git', 'add', '-A')
        except subprocess.CalledProcessError as exc:
            raise GitError(f'Failed to stage changes: {exc.stdout}') from exc

    def commit(self, message: str, description: str = '') -> bool:
        """Commit staged changes if present.

        Args:
            message: Commit subject line.
            description: Optional commit body.

        Returns:
            True if a commit was created, False if no changes were present.
        """
        if not self.has_changes():
            return False

        try:
            self.add_all()
            if description:
                self._run('git', 'commit', '-m', message, '-m', description)
            else:
                self._run('git', 'commit', '-m', message)
            return True
        except subprocess.CalledProcessError as exc:
            raise GitError(f'Failed to commit changes: {exc.stdout}') from exc

    def push(self, branch: str) -> None:
        """Push a branch to origin.

        Args:
            branch: Branch name to push.
        """
        try:
            self._run('git', 'push', '-u', 'origin', branch)
        except subprocess.CalledProcessError as exc:
            raise GitError(f'Failed to push branch {branch}: {exc.stdout}') from exc

    def commits_ahead(self, base: str) -> int:
        """Count commits ahead of origin/base.

        Args:
            base: Base branch name.

        Returns:
            Number of commits ahead.
        """
        try:
            result = self._run('git', 'log', '--oneline', f'origin/{base}..HEAD')
            return len([line for line in result.stdout.splitlines() if line.strip()])
        except subprocess.CalledProcessError as exc:
            raise GitError(f'Failed to count commits ahead of {base}: {exc.stdout}') from exc

    def _run(
        self,
        *args: str,
        check: bool = True,
        cwd: 'Optional[Path]' = _UNSET,  # type: ignore[assignment]
    ) -> subprocess.CompletedProcess[str]:
        """Run a git command in the working directory.

        Args:
            *args: Command arguments.
            check: Whether to raise on non-zero exit codes.
            cwd: Optional override for the working directory. Pass ``None`` to
                 run without a specific working directory (inherits the current
                 process cwd). When omitted the service's ``work_dir`` is used.

        Returns:
            CompletedProcess result.
        """
        if cwd is _UNSET:
            effective_cwd: Optional[str] = str(self.work_dir)
        elif cwd is None:
            effective_cwd = None
        else:
            effective_cwd = str(cwd)
        return subprocess.run(
            list(args),
            cwd=effective_cwd,
            capture_output=True,
            text=True,
            check=check,
        )
