import requests


def get_token(client_id: str) -> str:
    # Equivalent command: curl --location 'https://api.uhooinc.com/v1/generatetoken' --data-urlencode 'code=xxxxxxxx'

    url = "https://api.uhooinc.com/v1/generatetoken"
    data = {"code": client_id}
    response = requests.post(url, data=data)

    if response.status_code != 200:
        raise RuntimeError(f"Failed to get token: Response {response.status_code} - {response.text}")

    data = response.json()

    access_token = data["access_token"]
    # refresh_token = data["refresh_token"]

    return access_token


def get_device_list(access_token: str) -> list:
    # curl --location 'https://api.uhooinc.com/v1/devicelist' --header 'Authorization: Bearer xxxxxxxx'

    url = "https://api.uhooinc.com/v1/devicelist"
    data = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=data)

    if response.status_code != 200:
        raise RuntimeError(f"Failed to get token: Response {response.status_code} - {response.text}")
        # 201: invalid token
        # 400: limit exceeded

    return response.json()
