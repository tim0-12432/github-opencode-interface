from abc import ABC, abstractmethod

class AbstractStep(ABC):
    def __init__(self, name: str, retries: int = 0):
        self.name = name
        self.retries = retries

    def execute(self, env: dict={}):
        print(f"Executing step: {self.name} with {self.retries} retries")
        retries = 0
        while retries <= self.retries:
            try:
                self.run(env)
                break
            except Exception as e:
                print(f"Error executing step '{self.name}': {e}")
                retries += 1
                if retries > self.retries:
                    print(f"Step '{self.name}' failed after {self.retries} retries.")

    @abstractmethod
    def run(self, env: dict):
        raise NotImplementedError("Subclasses must implement the run method.")
