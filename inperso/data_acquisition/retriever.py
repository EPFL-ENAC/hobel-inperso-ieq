import logging
from abc import ABC, abstractmethod
from datetime import datetime

from inperso.data_acquisition.write import write


class Retriever(ABC):
    def __init__(self) -> None:
        """Container for retrieving data from a source and storing it in the database."""

        self.data: dict = {}

    def fetch(
        self,
        datetime_start: datetime,
        datetime_end: datetime,
    ) -> None:
        """Retrieve data and store it in the object."""

        self._check_datetimes(
            datetime_start=datetime_start,
            datetime_end=datetime_end,
        )

        self.data = self._fetch(
            datetime_start=datetime_start,
            datetime_end=datetime_end,
        )

    def _check_datetimes(
        self,
        datetime_start: datetime,
        datetime_end: datetime,
    ) -> None:
        """Check that the datetimes are valid for the source.

        Raises:
            ValueError: if the datetimes are invalid.
        """

        if datetime_end <= datetime_start:
            raise ValueError("datetime_end must be greater than datetime_start")

    @abstractmethod
    def _fetch(
        self,
        datetime_start: datetime,
        datetime_end: datetime,
    ) -> dict:
        """Retrieve data from the source and return it."""

    @abstractmethod
    def _get_line_queries(self) -> list[dict]:
        """Get line queries from stored data dictionary."""

    def store(self) -> None:
        queries = self._get_line_queries()
        logging.info(f"Writing {len(queries)} entries to the database.")
        write(queries)
