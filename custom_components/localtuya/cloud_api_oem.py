"""Cloud API implementation for Tuya OEM API."""
import functools
import logging
import hmac
import hashlib
import json

import requests
import time

from homeassistant.core import HomeAssistant

from .cloud_api import CloudApi

_TUYA_USER_AGENT = "TY-UA=APP/Android/1.1.6/SDK/null"
_TUYA_API_VERSION = "1.0"

_TUYA_KNOWN_VENDORS = {
    "ledvance": {
        "brand": "Ledvance",
        "client_id": "fx3fvkvusmw45d7jn8xh",
        "secret": "A_armptsqyfpxa4ftvtc739ardncett3uy_cgqx3ku34mh5qdesd7fcaru3gx7tyurr",
    },
    "positivo": {
        "brand": "Positivo",
        "client_id": "qk4c93xsttfjsm4ktr94",
        "secret": "A_9v5dh8yngmhtxdjen7t7qqx5ggmdf5su_w7vm9gr7meys387fpj7y7yrvx8w554cd",
    },
    "sylvania": {
        "brand": "Sylvania",
        "client_id": "creq75hn4vdg5qvrgryp",
        "secret": "A_ag4xcmp9rjttkj9yf9e8c3wfxry7yr44_wparh3scdv8dc7rrnuegaf9mqmn4snpk",
    },
    "birdlover": {
        "brand": "Birdlover",
        "client_id": "gmusrthh3sygeyv3sr38",
        "secret": "A_pku4cchspfmskfgtaacqcvkfdscx7u7t_x4y4ds9nysv4d3agjyqwmvnptwhgtcwu",
    },
    "gosund": {
        "brand": "Gosund",
        "client_id": "pwhnn4fa7ydkakf3nehn",
        "secret": "A_wm8hvxahqhcvvnpqgurympm4ppfgxxnm_pqdyxyx3uhk337sxxumdgfry3awaxysm",
    },
    "brennenstuhl": {
        "brand": "Brennenstuhl",
        "client_id": "dh35afm9ha79sppyxgkf",
        "secret": "A_9gyrek4h5ygwshsndqurwjkddtjpw9yr_aqy9p3e78xr5htpsn95fss5rvcdtaahd",
    },
    "nedis": {
        "brand": "Nedis",
        "client_id": "pettfwyepwpwwhxy57gp",
        "secret": "A_73p8kvkhsted5fxvx8pfudk5hwtmnjr3_yptwxx4t9rkmcppyagwpd43y77tnpw8s",
    },
    "treatlife": {
        "brand": "Treatlife",
        "client_id": "8yncru89qa8495mdutya",
        "secret": "A_37enmfsnr4r3w8j5cd3fxmhm97gaatxx_y4gn37gryf5ufqhqgh99r9wp3h44dp95",
    },
    "lsc": {
        "brand": "LSC",
        "client_id": "q594qaqdpy89gmvyndtp",
        "secret": "A_yegjfwuukevd8qfxw3rjfr5sj43p5gpr_xh59e8qykn4sp7jyh7rwaq3ykfwf8e5n",
    },
    "overmax": {
        "brand": "Overmax",
        "client_id": "um7ysycqag83et8drf8n",
        "secret": "A_jpjmj4vp5gvwmdpf8hk5yjkrj3teegve_kwqsmrup5qrx4rpgssrkt7dngq8c53q9",
    },
    "settiplus": {
        "brand": "Setti+",
        "client_id": "8fjupshhjwqq4auxtd4m",
        "secret": "A_4eqrx7y3sygqv5eragnwxnetv3epsj4f_svhcum73wnvaehgv88wdj5dddfxrt48u",
    },
    "nous": {
        "brand": "Nous",
        "client_id": "dhs3xggvwehvc5tj9xqp",
        "secret": "A_wwwrnvy7gayy9dvp5nuahyd5d3j4kyxp_7vgwxdy589jtwwee7rugayxrderkekww",
    },
    "woox": {
        "brand": "Woox Home",
        "client_id": "pyxevcmw83jg83qca9c7",
        "secret": "A_e3g9q4enqeew9x7xgcqkn8jjcdgwf8py_h8wv7dea7u4hnfc8k8qagr897yuc79ar",
    },
    "maxcom": {
        "brand": "Maxcom Home",
        "client_id": "83f54m7c4wpmp48a377e",
        "secret": "A_n33asm4fv3yud9pcjfuxcycspy7fhx3g_kvjavqmjyf3v5wk9s55fgeewgkgjnhc9",
    },
    "calex": {
        "brand": "Calex Smart",
        "client_id": "xh8txuxq9juy48e5q39w",
        "secret": "A_u7mn44dkwx3qqe4kkakc4p933au5fnkr_g9egj8jjgup8ctpxjknye5ar4wxghesa",
    },
    "smartdgm": {
        "brand": "SmartDGM",
        "client_id": "ryvgvwmtydwvsh3hd7rr",
        "secret": "A_gmjvan774aag5u8ksjtt8dvyas8pvg8j_g3xtrhk4rxpeqxuneqmrx54dqy4htda3",
    },
    "gridconnect": {
        "brand": "GridConnect",
        "client_id": "k584ttaqt7f4huakhtgp",
        "secret": "A_yg7pds9ap4vd3vj8t8cjy5agvj4jygay_c5t98m3kp7atcnspggcqewp5cqhnfuum",
    },
    "spectrum": {
        "brand": "Spectrum Smart",
        "client_id": "t8aygqqdh8u7nd5j5kcf",
        "secret": "A_avfpxsmwwt9txxg8eyd4pppfdqdyydqg_xsxdsvwgt7kdpe8xj38nvkxw4gaw4dkh",
    },
}

_LOGGER = logging.getLogger(__name__)


class TuyaCloudApiOEM(CloudApi):
    """
    Class that logins and lists devices via the Tuya OEM API.

    The returned device list mimics that of the Tuya IoT Platform API.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        cloud_type: str,
        region: str,
        username: str,
        password: str,
        client_id: str,
        secret: str,
    ):
        """Initialize the class."""
        super().__init__(cloud_type)

        self._hass = hass
        self._endpoint = f"https://a1.tuya{region}.com/api.json"
        self._username = username
        self._password = password

        # It works with empty country code but the parameter must be sent nonetheless
        self._country_code = ""

        if cloud_type.startswith("oem_"):
            vendor = cloud_type.replace("oem_", "")
        else:
            raise ValueError("Cloud type must be one of the oem_xxx types")

        if vendor in _TUYA_KNOWN_VENDORS:
            self._client_id = _TUYA_KNOWN_VENDORS[vendor]["client_id"]
            self._secret = _TUYA_KNOWN_VENDORS[vendor]["secret"]
            self._brand = _TUYA_KNOWN_VENDORS[vendor]["brand"]
        elif vendor == "generic":
            self._client_id = client_id
            self._secret = secret
            self._brand = "generic"
        else:
            raise ValueError(f"Unknown vendor {vendor}")

        self._session = requests.session()
        self._sid = None

    async def _async_api(
        self, action, payload=None, extra_params=None, requires_sid=True
    ):
        headers = {"User-Agent": _TUYA_USER_AGENT}

        if extra_params is None:
            extra_params = {}

        params = {
            "a": action,
            "clientId": self._client_id,
            "v": _TUYA_API_VERSION,
            "time": str(int(time.time())),
            **extra_params,
        }

        if requires_sid:
            if self._sid is None:
                raise ValueError("You need to login first.")
            params["sid"] = self._sid

        data = {}
        if payload is not None:
            data["postData"] = json.dumps(payload, separators=(",", ":"))

        params["sign"] = self._sign({**params, **data})

        func = functools.partial(
            self._session.post,
            self._endpoint,
            params=params,
            data=data,
            headers=headers,
        )

        _LOGGER.debug("Request: headers %s, params %s, data %s", headers, params, data)

        result = await self._hass.async_add_executor_job(func)
        result = self._handle(result.json())

        _LOGGER.debug("Result: %s", result)

        return result

    def _sign(self, data):
        keys_not_to_sign = ["gid"]

        sorted_keys = sorted(list(data.keys()))

        # Create string to sign
        str_to_sign = ""
        for key in sorted_keys:
            if key in keys_not_to_sign:
                continue
            if key == "postData":
                if len(str_to_sign) > 0:
                    str_to_sign += "||"
                str_to_sign += key + "=" + self._mobile_hash(data[key])
            else:
                if len(str_to_sign) > 0:
                    str_to_sign += "||"
                str_to_sign += key + "=" + data[key]

        return hmac.new(
            bytes(self._secret, "utf-8"),
            msg=bytes(str_to_sign, "utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def _mobile_hash(data):
        prehash = hashlib.md5(bytes(data, "utf-8")).hexdigest()
        return prehash[8:16] + prehash[0:8] + prehash[24:32] + prehash[16:24]

    @staticmethod
    def _handle(result):
        if result["success"]:
            return result["result"]
        if result["errorCode"] == "USER_SESSION_INVALID":
            raise InvalidUserSession(result["errorMsg"])
        if result["errorCode"] == "USER_PASSWD_WRONG":
            raise InvalidAuthentication(result["errorMsg"])
        raise ValueError(f"{result['errorMsg']} ({result['errorCode']})")

    @staticmethod
    def _plain_rsa_encrypt(modulus, exponent, message):
        """Encrypt message using plain (textbook) RSA encrypt."""
        message_int = int.from_bytes(message, "big")
        enc_message_int = pow(message_int, exponent, modulus)
        return enc_message_int.to_bytes(256, "big")

    def _enc_password(self, modulus, exponent, password):
        passwd_hash = hashlib.md5(password.encode("utf8")).hexdigest().encode("utf8")
        return self._plain_rsa_encrypt(int(modulus), int(exponent), passwd_hash).hex()

    async def _async_login(self):
        payload = {"countryCode": self._country_code, "email": self._username}
        token_info = await self._async_api(
            "tuya.m.user.email.token.create", payload, requires_sid=False
        )

        payload = {
            "countryCode": self._country_code,
            "email": self._username,
            "ifencrypt": 1,
            "options": '{"group": 1}',
            "passwd": self._enc_password(
                token_info["publicKey"], token_info["exponent"], self._password
            ),
            "token": token_info["token"],
        }
        login_info = await self._async_api(
            "tuya.m.user.email.password.login", payload, requires_sid=False
        )

        self._sid = login_info["sid"]

    async def _async_list_devices(self, retry_login=True):
        try:
            await self._async_list_devices_no_retry()
        except InvalidUserSession as err:
            # If session expired - retry login and operation once again
            if retry_login:
                _LOGGER.warning("User session expired, trying to re-login.")
                await self._async_login()
                await self._async_list_devices_no_retry()
            else:
                raise err

    async def _async_list_devices_no_retry(self):
        devs = {}
        # First fetch all "groups", i.e. homes
        for group in await self._async_api("tuya.m.location.list"):
            # Then fetch devices for each group and merge into a single list
            for dev in await self._async_api(
                "tuya.m.my.group.device.list", extra_params={"gid": group["groupId"]}
            ):
                # Map each device to the same format as the IoT Platform API
                devs[dev["devId"]] = self._map_device(dev)
        self._device_list = devs

    def _map_device(self, dev):
        category = dev["category"]
        model = f"{self._brand} {CloudApi.product_from_category(category)}"
        return {
            "id": dev["devId"],
            "category": category,
            "product_id": dev["productId"],
            "product_name": model,
            "model": model,
            "name": dev["name"],
            "local_key": dev["localKey"],
        }

    @staticmethod
    async def _invoke_handle_error(func: callable):
        try:
            await func()
        except ValueError as err:
            return str(err)

        return "ok"

    async def _async_authenticate(self):
        return await self._invoke_handle_error(self._async_login)

    async def _async_fetch_device_list(self):
        return await self._invoke_handle_error(self._async_list_devices)


class InvalidUserSession(ValueError):
    """Invalid user session error."""


class InvalidAuthentication(ValueError):
    """Invalid authentication error."""
