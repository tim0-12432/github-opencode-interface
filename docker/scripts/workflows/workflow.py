from abc import ABC
from .steps.step import AbstractStep


class AbstractWorkflow(ABC):
    def __init__(self, name: str, steps: list[AbstractStep]):
        self.name = name
        self.steps = steps

    def run(self, env: dict = {}):
        print(f"Running workflow: {self.name}")
        for step in self.steps:
            print(f"Executing step: {step}")
            step.execute(env)
