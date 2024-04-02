from datetime import datetime

from inperso.data_acquisition.retriever import Retriever


class AirlyRetriever(Retriever):
    def _fetch(
        self,
        datetime_start: datetime,
        datetime_end: datetime,
    ) -> dict:
        """Retrieve data from the source and return it."""
        raise NotImplementedError()

    def _get_line_queries(self) -> list[str]:
        """Get line queries from stored data dictionary."""
        raise NotImplementedError()
