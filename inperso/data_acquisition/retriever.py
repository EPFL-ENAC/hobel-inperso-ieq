from abc import ABC, abstractmethod
from typing import Optional


class Retriever(ABC):
    def __init__(self):
        """Container for retrieving data from a source and storing it in the database."""

        self.data: Optional[dict] = None

    @abstractmethod
    def retrieve(self):
        pass

    @abstractmethod
    def get_line_queries(self):
        pass

    def store(self):
        # TODO
        raise NotImplementedError()
