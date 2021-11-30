import requests
import json
from helper_tools import MyHelp as h


class ApiComm:
    def __init__(self, url, endpoint):
        self.endpoint = endpoint
        self._headers = {"content-type": "application/json"}
        self._url = url

    @property
    def url(self):
        # l.debug(self._url+self.endpoint)
        return self._url + self.endpoint

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        pass

    def post(self, to_send, endpoint=None):
        if endpoint:
            self.endpoint = endpoint
        result = None
        try:
            result = requests.post(
                self.url, headers=self._headers, data=json.dumps(to_send), timeout=2
            )
        except:
            pass
        return result

    def post_code(self, to_send):
        data = self.post(to_send)
        if data:
            return data.status_code
        else:
            return "Not found"

    def get(self, params):
        result = requests.post(
            self.url, headers=self._headers, data=json.dumps(params), timeout=2
        )
        return result


# Komunikace s ApiDaemonem
class ApiHA(ApiComm):
    def __init__(self, endpoint="service"):
        super().__init__("http://192.168.0.2:5050/api/appdaemon/", endpoint)


# Komunikaci s HA
class ApiHADirect(ApiComm):
    def __init__(self):
        authorization = "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiIwYzNjZTNjZGNhZjg0NjM3OGUzZmQ2N2MzYjAwZjM1ZSIsImlhdCI6MTYwNTE5MTQ0MSwiZXhwIjoxOTIwNTUxNDQxfQ.RIrTbdayT4J-ah6z7TpGue-xOogSV9LQoKT6gPzGIp4"
        super().__init__("http://192.168.0.2:8123/", "api")
        self._headers = {
            "Authorization": authorization,
            "Content-Type": "application/json",
        }

    def state(self, entity_id):
        url = f"{self.url}/states/{entity_id}"
        result = requests.get(url, headers=self._headers, timeout=2)
        if result.status_code == 200:
            return json.loads(result.text)
        return None

    def state_extract(self, entity_id) -> str:
        s = self.state(entity_id)
        if s and ("state" in s):
            return s["state"]
        else:
            return ""

    def is_entity_on(self, entity_id) -> bool:
        return self.state_extract(entity_id) == "on"

    def is_entity_off(self, entity_id) -> bool:
        return self.state_extract(entity_id) == "off"

    def turn_on(self, entity_id):
        url = f"{self.url}/services/input_boolean/turn_on"
        to_send = {"entity_id": entity_id}
        requests.post(url, headers=self._headers, data=json.dumps(to_send), timeout=2)

    def turn_off(self, entity_id):
        url = f"{self.url}/services/input_boolean/turn_off"
        to_send = {"entity_id": entity_id}
        requests.post(url, headers=self._headers, data=json.dumps(to_send), timeout=2)


class ApiAssistant(ApiComm):
    def __init__(self):
        ip_address = "192.168.0.2"
        http = f"http://{ip_address}:5050/"
        super().__init__(http, "api")


if __name__ == "__main__":
    api = ApiHADirect()
    r = api.state("sensor.openweathermap_temperature")
