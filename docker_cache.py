#!/usr/bin/env python3
"""Shared Docker image caching helpers."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Optional, Protocol

HASH_LABEL = 'com.github-opencode-interface.content-hash'

_HASH_TARGETS = [
    'docker/Dockerfile',
    'docker/scripts/lib',
    'docker/scripts/orchestrator.sh',
    'docker/prompts',
    'docker/opencode',
    'auth.json',
]


class Hasher(Protocol):
    def update(self, data: bytes) -> None:
        ...


def _collect_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for rel in _HASH_TARGETS:
        target = repo_root / rel
        if not target.exists():
            if rel == 'auth.json':
                continue
            raise FileNotFoundError(f'Missing hash input: {target}')
        if target.is_file():
            files.append(target)
        else:
            files.extend(
                sorted(
                    (p for p in target.rglob('*') if p.is_file()),
                    key=lambda p: p.relative_to(repo_root).as_posix(),
                )
            )
    return sorted(files, key=lambda p: p.relative_to(repo_root).as_posix())


def _hash_file(hasher: Hasher, repo_root: Path, path: Path) -> None:
    rel_path = path.relative_to(repo_root).as_posix()
    hasher.update(rel_path.encode('utf-8'))
    hasher.update(b'\0')
    with path.open('rb') as handle:
        while chunk := handle.read(1024 * 1024):
            hasher.update(chunk)
    hasher.update(b'\0')


def calculate_repo_hash(repo_root: str) -> str:
    """Calculate a deterministic SHA256 hash of Docker build inputs."""
    root_path = Path(repo_root).resolve()
    hasher = hashlib.sha256()
    for file_path in _collect_files(root_path):
        _hash_file(hasher, root_path, file_path)
    return hasher.hexdigest()


def get_image_hash_label(image_name: str) -> Optional[str]:
    """Return the stored content hash label for the image if present."""
    try:
        result = subprocess.run(
            [
                'docker',
                'inspect',
                f'--format={{index .Config.Labels "{HASH_LABEL}"}}',
                image_name,
            ],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError('Docker executable not found. Is Docker installed and on PATH?') from exc

    if result.stderr and 'Cannot connect to the Docker daemon' in result.stderr:
        raise RuntimeError('Cannot connect to the Docker daemon. Is it running?')

    if result.returncode != 0:
        return None

    value = result.stdout.strip()
    if not value or value in {'<no value>', 'null'}:
        return None
    return value


def build_docker_image(
    dockerfile_path: str,
    image_name: str,
    content_hash: str,
    verbose: bool,
) -> bool:
    """Build the Docker image with the provided content hash label."""
    try:
        if verbose:
            result = subprocess.run(
                [
                    'docker',
                    'build',
                    '--label',
                    f'{HASH_LABEL}={content_hash}',
                    '-t',
                    image_name,
                    '-f',
                    dockerfile_path,
                    '.',
                ],
                stdout=None,
                stderr=subprocess.PIPE,
                text=True,
            )
        else:
            result = subprocess.run(
                [
                    'docker',
                    'build',
                    '--label',
                    f'{HASH_LABEL}={content_hash}',
                    '-t',
                    image_name,
                    '-f',
                    dockerfile_path,
                    '.',
                ],
                capture_output=True,
                text=True,
            )
    except FileNotFoundError as exc:
        raise RuntimeError('Docker executable not found. Is Docker installed and on PATH?') from exc

    if result.stderr and 'Cannot connect to the Docker daemon' in result.stderr:
        raise RuntimeError('Cannot connect to the Docker daemon. Is it running?')

    return result.returncode == 0


def should_rebuild_image(
    repo_root: str,
    image_name: str,
    force_build: bool,
) -> tuple[bool, str]:
    """Determine whether the Docker image needs to be rebuilt."""
    current_hash = calculate_repo_hash(repo_root)
    if force_build:
        return True, current_hash

    existing_hash = get_image_hash_label(image_name)
    if existing_hash is None:
        return True, current_hash

    return existing_hash != current_hash, current_hash
