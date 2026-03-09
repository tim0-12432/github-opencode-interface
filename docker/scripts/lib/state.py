'''File-backed state management for workflows.'''

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .exceptions import StateError


@dataclass
class StateManager:
    '''Manage workflow state stored as files in a directory.'''

    state_dir: Path

    def init(self) -> None:
        '''Ensure the state directory exists.'''
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def save(self, key: str, value: str) -> None:
        '''Save a value to a state key.

        Args:
            key: State key name.
            value: State value to persist.
        '''
        try:
            self.init()
            (self.state_dir / key).write_text(value, encoding='utf-8')
        except OSError as exc:
            raise StateError(f'Failed to save state for key {key}.') from exc

    def load(self, key: str, default: str = '') -> str:
        '''Load a state value, returning a default if missing.

        Args:
            key: State key name.
            default: Default value when key is missing.

        Returns:
            Stored value or default.
        '''
        path = self.state_dir / key
        if not path.exists():
            return default
        try:
            return path.read_text(encoding='utf-8')
        except OSError as exc:
            raise StateError(f'Failed to load state for key {key}.') from exc

    def save_test_output(self, output: str) -> None:
        '''Persist the latest test output.

        Args:
            output: Test output text.
        '''
        self.save('last_test_output', output)

    def get_test_output(self) -> str:
        '''Return the latest test output, or a default message.'''
        return self.load('last_test_output', 'No test output available')

    def save_review_feedback(self, feedback: str) -> None:
        '''Persist the latest review feedback.

        Args:
            feedback: Review feedback text.
        '''
        self.save('last_review_feedback', feedback)

    def get_review_feedback(self) -> str:
        '''Return the latest review feedback.'''
        return self.load('last_review_feedback', '')

    def get_review_report(self, report_type: str) -> str:
        '''Return the stored review report for a type.

        Args:
            report_type: Report type identifier.

        Returns:
            Review report contents or default message.
        '''
        return self.load(f'{report_type}_review_report', 'No review report available')

    def cleanup(self) -> None:
        '''Strip file extensions from state files in the directory.'''
        self.init()
        for file_path in self.state_dir.glob('*.*'):
            if not file_path.is_file():
                continue
            new_path = file_path.with_suffix('')
            try:
                file_path.replace(new_path)
            except OSError as exc:
                raise StateError('Failed to cleanup state files.') from exc

    def clear(self) -> None:
        '''Remove all state files.'''
        if not self.state_dir.exists():
            return
        for file_path in self.state_dir.iterdir():
            if file_path.is_file():
                try:
                    file_path.unlink()
                except OSError as exc:
                    raise StateError('Failed to clear state files.') from exc
