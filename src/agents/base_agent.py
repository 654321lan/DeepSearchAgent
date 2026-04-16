from abc import ABC, abstractmethod

class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def process(self, input_data: dict) -> dict:
        pass

    def __repr__(self):
        return f"<Agent {self.name}>"