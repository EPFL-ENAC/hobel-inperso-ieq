import requests

from inperso.data_acquisition.retriever import Retriever


class AirthingsRetriever(Retriever):
    def retrieve(self):
        # TODO
        pass

    def get_line_queries(self):
        # TODO
        pass


def authorize():
    url = "https://accounts.airthings.com/authorize"
