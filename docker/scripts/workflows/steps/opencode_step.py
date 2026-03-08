import subprocess
from .step import AbstractStep
from abc import abstractmethod

ModelLow = "low"
ModelStandard = "standard"
ModelHigh = "high"

class AbstractOpencodeStep(AbstractStep):
    def __init__(self, name: str, model: str, prompt: str, retries: int = 0):
        super().__init__(name, retries)
        self.model = model
        self.prompt = prompt

    @abstractmethod
    def preprocess(self):
        raise NotImplementedError("Subclasses must implement this method")
    
    @abstractmethod
    def postprocess(self, response):
        raise NotImplementedError("Subclasses must implement this method")

    def run(self, env: dict):
        self.preprocess()
        try:
            response = subprocess.check_output([
                "opencode",
                "run",
                "--model", self.model,
            ], text=True, input=self.prompt, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            print(f"Error calling OpenCode: {e}")
            raise
        self.postprocess(response)
