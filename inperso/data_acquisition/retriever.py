import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone

from inperso import config
from inperso.data_acquisition.read_db import query
from inperso.data_acquisition.write_db import write


class Retriever(ABC):
    def __init__(self) -> None:
        """Container for retrieving data from a source and storing it in the database."""

        self.data: dict = {}

    @property
    @abstractmethod
    def _measurement_name(self) -> str:
        """Name of the measurement in the database."""

    @property
    @abstractmethod
    def _fetch_interval(self) -> timedelta:
        """Interval for fetching data from the source."""

    def fetch_recent_and_store(self) -> None:
        """Retrieve most recent data and store it in the database."""

        datetime_start = self.get_latest_retrieval_datetime()
        datetime_end = datetime.now(timezone.utc)
        self.fetch_and_store(datetime_start, datetime_end)

    def fetch_and_store(self, datetime_start: datetime, datetime_end: datetime) -> None:
        """Retrieve data from the source and store it in the database."""

        logging.info(f"Will fetch data for {self._measurement_name} from {datetime_start} to {datetime_end}.")

        n_fragments = (datetime_end - datetime_start) // self._fetch_interval

        for i in range(n_fragments + 1):
            datetime_start_fragment = datetime_start + i * self._fetch_interval
            datetime_end_fragment = datetime_start_fragment + self._fetch_interval
            datetime_end_fragment = min(datetime_end_fragment, datetime_end)
            if datetime_start_fragment >= datetime_end_fragment:
                break

            logging.info(
                f"Fetching data for {self._measurement_name} from {datetime_start_fragment} to {datetime_end_fragment}."
            )

            self.fetch(
                datetime_start=datetime_start_fragment,
                datetime_end=datetime_end_fragment,
            )
            self.store()

    def get_latest_retrieval_datetime(self) -> datetime:
        """Get the most recent datetime for the measurement associated with the retriever."""

        query_str = (
            f'from(bucket:"{config.db["bucket"]}") '
            "|> range(start: 0, stop: now()) "
            f'|> filter(fn: (r) => r["_measurement"] == "{self._measurement_name}") '
            '|> sort(columns: ["_time"], desc: false) '
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

        if datetime_end - datetime_start > self._fetch_interval:
            raise ValueError(f"Time interval too long for {self.__class__.__name__}, maximum is {self._fetch_interval}")

    @abstractmethod
    def _fetch(
        self,
        datetime_start: datetime,
        datetime_end: datetime,
    ) -> dict:
        """Retrieve data from the source and return it."""

    @abstractmethod
    def _get_line_queries(self) -> list[dict]:
        """Get line queries from stored data dictionary.

        Shound return a list of dictionaries with the structure:
        {
            "measurement": str,
            "tags": dict,
            "fields": dict,
            "time": datetime or int (unix timestamp),
        }
        """

    def store(self) -> None:
        queries = self._get_line_queries()
        logging.info(f"Writing {len(queries)} entries to the database.")
        write(queries)
