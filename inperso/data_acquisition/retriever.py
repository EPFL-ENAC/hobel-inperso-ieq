import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone

from inperso import config
from inperso.database.read import query
from inperso.database.write import WriteQuery, write


class Retriever(ABC):
    def __init__(self) -> None:
        """Container for retrieving data from a source and storing it in the database."""

        self._write_queries: list[WriteQuery] = []

    @property
    @abstractmethod
    def _measurement_name(self) -> str:
        """Name of the measurement in the database."""

    @property
    @abstractmethod
    def _fetch_interval(self) -> timedelta:
        """Interval for fetching data from the source."""

    def fetch_recent(self) -> None:
        """Retrieve most recent data and store it in the database."""

        datetime_start = self.get_latest_retrieval_datetime()
        datetime_end = datetime.now(timezone.utc)
        self.fetch(datetime_start, datetime_end)

    def fetch(self, datetime_start: datetime, datetime_end: datetime) -> None:
        """Retrieve data from the source and store it in the database."""

        logging.info(f"Will fetch data for {self._measurement_name} from {datetime_start} to {datetime_end}.")

        n_fragments = (datetime_end - datetime_start) // self._fetch_interval

        for i in range(n_fragments + 1):
            datetime_start_fragment = datetime_start + i * self._fetch_interval
            datetime_end_fragment = datetime_start_fragment + self._fetch_interval
            datetime_end_fragment = min(datetime_end_fragment, datetime_end)
            if datetime_start_fragment.replace(microsecond=0) >= datetime_end_fragment.replace(microsecond=0):
                break

            logging.info(
                f"Fetching data for {self._measurement_name} from {datetime_start_fragment} to {datetime_end_fragment}."
            )

            self._fetch(
                datetime_start=datetime_start_fragment,
                datetime_end=datetime_end_fragment,
            )
            self._store()

    def fetch_from_file(self, file_path: str, *args, **kwargs) -> None:
        """Retrieve data from a file and store it in the database."""

        self._fetch_from_file(file_path, *args, **kwargs)
        self._store()

    def get_latest_retrieval_datetime(self) -> datetime:
        """Get the most recent datetime for the measurement associated with the retriever."""

        query_str = (
            f'from(bucket:"{config.db["bucket"]}") '
            "|> range(start: 0, stop: now()) "
            f'|> filter(fn: (r) => r["_measurement"] == "{self._measurement_name}") '
            "|> last() "
        )
        result = query(query_str)

        if len(result) == 0:
            logging.info(f"No data found for {self._measurement_name}.")
            # TODO: get datetime_start from config when API keys are unlimited
            # datetime_start = config.config["datetime_start"]
            datetime_start = datetime.now(timezone.utc) - timedelta(hours=1)

        else:
            datetime_start = result[0].records[0].get_time()

        return datetime_start

    def add_write_query(self, write_query: WriteQuery) -> None:
        """Store a write query and write to database if enough queries accumulated."""

        self._write_queries.append(write_query)

        if len(self._write_queries) >= config.db["minimum_write_batch_size"]:
            self._store()

    @abstractmethod
    def _fetch(
        self,
        datetime_start: datetime,
        datetime_end: datetime,
    ) -> None:
        """Retrieve data from the source while regularly calling self.add_write_query."""

    def _fetch_from_file(self, file_path: str, *args, **kwargs) -> None:
        """Retrieve data from a file while regularly calling self.add_write_query."""

        raise NotImplementedError("Retriever does not support fetching from a file.")

    def _store(self) -> None:
        if len(self._write_queries) == 0:
            return

        logging.info(f"Writing {len(self._write_queries)} entries to the database.")
        write(self._write_queries)
        self._write_queries = []
