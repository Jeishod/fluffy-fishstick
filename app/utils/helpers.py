import base64
import hashlib
import hmac
import time
import uuid

from app.utils.enums import RequestMethod


def gen_hashed_string(api_secret: str, message: str) -> bytes:
    result = base64.b64encode(
        hmac.new(
            key=api_secret.encode("utf-8"),
            msg=message.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest(),
    )
    return result


def get_sign_string(method: RequestMethod, endpoint: str, data_json: str = "") -> [int, str]:
    timestamp = int(time.time() * 1000)
    sign_string = str(timestamp) + method + endpoint + data_json
    return timestamp, sign_string


def gen_request_id() -> str:
    request_id = str(uuid.uuid4())
    return request_id
