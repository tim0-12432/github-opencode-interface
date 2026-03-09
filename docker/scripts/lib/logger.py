'''Rich-backed logging utilities for workflows.'''

from __future__ import annotations

from datetime import datetime
import logging
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler


class WorkflowLogger:
    '''Colored logger with workflow-friendly helpers.'''

    def __init__(self, verbose: bool = False, console: Optional[Console] = None) -> None:
        '''Initialize the logger.

        Args:
            verbose: When true, enables verbose output.
            console: Optional Rich console instance.
        '''
        self._console = console or Console()
        self._logger = logging.getLogger('workflow')
        self._logger.handlers.clear()
        handler = RichHandler(
            console=self._console,
            show_time=False,
            show_level=False,
            show_path=False,
            markup=True,
            rich_tracebacks=True,
        )
        handler.setFormatter(logging.Formatter('%(message)s'))
        self._logger.addHandler(handler)
        self._logger.setLevel(logging.DEBUG)
        self._verbose = verbose

    def log(self, message: str) -> None:
        '''Log a standard informational message.

        Args:
            message: Message to log.
        '''
        self._emit(message, level=logging.INFO)

    def success(self, message: str) -> None:
        '''Log a success message.

        Args:
            message: Message to log.
        '''
        self._emit(message, prefix='✓', color='green', level=logging.INFO)

    def error(self, message: str) -> None:
        '''Log an error message.

        Args:
            message: Message to log.
        '''
        self._emit(message, prefix='✗', color='red', level=logging.ERROR)

    def warn(self, message: str) -> None:
        '''Log a warning message.

        Args:
            message: Message to log.
        '''
        self._emit(message, prefix='!', color='yellow', level=logging.WARNING)

    def phase(self, title: str) -> None:
        '''Log a phase banner.

        Args:
            title: Phase title to display.
        '''
        line = '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
        self._console.print('')
        self._console.print(f'[cyan]{line}[/cyan]')
        self._console.print(f'[cyan]  {title}[/cyan]')
        self._console.print(f'[cyan]{line}[/cyan]')
        self._console.print('')

    def verbose(self, message: str) -> None:
        '''Log a verbose message when enabled.

        Args:
            message: Message to log.
        '''
        if not self._verbose:
            return
        self._emit(message, prefix='DEBUG', color='blue', level=logging.DEBUG)

    def banner(self, title: str) -> None:
        '''Print a banner with a title.

        Args:
            title: Banner title.
        '''
        line = '════════════════════════════════════════════════════════════'
        self._console.print('')
        self._console.print(f'[cyan]╔{line}╗[/cyan]')
        self._console.print(f'[cyan]║{title.center(len(line))}║[/cyan]')
        self._console.print(f'[cyan]╚{line}╝[/cyan]')
        self._console.print('')

    def _emit(
        self,
        message: str,
        *,
        prefix: str | None = None,
        color: str | None = None,
        level: int = logging.INFO,
    ) -> None:
        timestamp = datetime.now().strftime('%H:%M:%S')
        time_text = f'[blue][{timestamp}][/blue]'
        prefix_text = ''
        if prefix is not None:
            if color:
                prefix_text = f'[{color}]{prefix}[/] '
            else:
                prefix_text = f'{prefix} '
        self._logger.log(level, f'{time_text} {prefix_text}{message}')
