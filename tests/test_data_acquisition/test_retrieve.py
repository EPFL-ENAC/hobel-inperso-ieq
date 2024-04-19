from datetime import datetime, timedelta, timezone

import pytest
from pytest_mock import MockFixture

from inperso.data_acquisition.airly import AirlyRetriever
from inperso.data_acquisition.airthings import AirthingsRetriever
from inperso.data_acquisition.qualtrics import QualtricsRetriever
from inperso.data_acquisition.retrieve import main
from inperso.data_acquisition.retriever import Retriever
from inperso.data_acquisition.uhoo import UhooRetriever


@pytest.mark.parametrize(
    "DerivedRetriever",
    [
        AirlyRetriever,
        AirthingsRetriever,
        QualtricsRetriever,
        UhooRetriever,
    ],
)
def test_main(
    mocker: MockFixture,
    DerivedRetriever: type[Retriever],
):
    """Test that the retrievers' fetch and store methods are called."""

    retriever_module_path = f"{Retriever.__module__}.{Retriever.__name__}"
    derived_retriever_module_path = f"{DerivedRetriever.__module__}.{DerivedRetriever.__name__}"

    # Mock the lookup of the latest retrieval datetime
    datetime_start = datetime.now(timezone.utc) - timedelta(hours=0.5)
    mocker.patch(f"{retriever_module_path}.get_latest_retrieval_datetime", return_value=datetime_start)

    # Mock the fetch and store methods
    mocker.patch(f"{retriever_module_path}._fetch")
    mocker.patch(f"{retriever_module_path}._store")
    fetch_mock = mocker.patch(f"{derived_retriever_module_path}._fetch")
    store_mock = mocker.patch(f"{derived_retriever_module_path}._store")

    main()

    assert fetch_mock.call_count == 1
    assert store_mock.call_count == 1
