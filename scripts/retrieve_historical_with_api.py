from datetime import datetime, timezone

import inperso

datetime_start = datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
datetime_end = datetime.now(timezone.utc)
retriever = inperso.data_acquisition.AirthingsRetriever()
retriever.fetch(datetime_start, datetime_end)
