'''Custom exceptions for the workflow system.'''


class WorkflowError(Exception):
    '''Base exception for workflow-related errors.'''


class StepError(WorkflowError):
    '''Base exception for workflow step failures.'''


class StepExecutionError(StepError):
    '''Raised when a step fails during execution.'''


class StepRetryExhaustedError(StepError):
    '''Raised when a step fails after all retries are exhausted.'''


class ValidationError(WorkflowError):
    '''Raised when configuration or inputs fail validation.'''


class GitHubError(WorkflowError):
    '''Raised when GitHub operations fail.'''




class GitError(WorkflowError):
    '''Raised when git operations fail.'''


class OpenCodeError(WorkflowError):
    '''Raised when OpenCode operations fail.'''


class StateError(WorkflowError):
    '''Raised when state storage or retrieval fails.'''


class ConfigError(WorkflowError):
    '''Raised when configuration is invalid or incomplete.'''
