from flask import Flask, request, jsonify
import hmac
import hashlib
import requests
import string
import random
import secrets
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import json
from protobuf_decoder.protobuf_decoder import Parser
import codecs
import time
from datetime import datetime
import urllib3
import base64
import concurrent.futures
import threading
import os
import re

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)


FORCE_REGION = "ID"
FORCE_PASS_PREFIX = "ZYX-HAX"
FORCE_NAME_PREFIX = "ZYX"



hex_key = "32656534343831396539623435393838343531343130363762323831363231383734643064356437616639643866376530306331653534373135623764316533"
key = bytes.fromhex(hex_key)

REGION_LANG = {"ME": "ar","IND": "hi","ID": "id","VN": "vi","TH": "th","BD": "bn","PK": "ur","TW": "zh","EU": "en","RU": "ru","NA": "en","SAC": "es","BR": "pt"}

REGION_URLS = {
    "IND": "https://client.ind.freefiremobile.com/",
    "ID": "https://clientbp.ggblueshark.com/",
    "BR": "https://client.us.freefiremobile.com/",
    "ME": "https://clientbp.common.ggbluefox.com/",
    "VN": "https://clientbp.ggblueshark.com/",
    "TH": "https://clientbp.common.ggbluefox.com/",
    "RU": "https://clientbp.ggblueshark.com/",
    "BD": "https://clientbp.ggblueshark.com/",
    "PK": "https://clientbp.ggblueshark.com/",
    "SG": "https://clientbp.ggblueshark.com/",
    "NA": "https://client.us.freefiremobile.com/",
    "SAC": "https://client.us.freefiremobile.com/",
    "EU": "https://clientbp.ggblueshark.com/",
    "TW": "https://clientbp.ggblueshark.com/"
}

def get_region(language_code: str) -> str:
    return REGION_LANG.get(language_code)

def get_region_url(region_code: str) -> str:
    return REGION_URLS.get(region_code, None)


STATS = {
    'total_requests': 0,
    'total_success': 0,
    'total_fail': 0,
    'last_success_at': None,
    'last_fail_at': None,
}
STATS_LOCK = threading.Lock()

def record_success():
    with STATS_LOCK:
        STATS['total_requests'] += 1
        STATS['total_success'] += 1
        STATS['last_success_at'] = datetime.now().isoformat()

def record_fail():
    with STATS_LOCK:
        STATS['total_requests'] += 1
        STATS['total_fail'] += 1
        STATS['last_fail_at'] = datetime.now().isoformat()


thread_local = threading.local()

def get_session():
    if not hasattr(thread_local, "session"):
        thread_local.session = requests.Session()
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        retry_strategy = Retry(
            total=2,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=100, pool_maxsize=100)
        thread_local.session.mount("http://", adapter)
        thread_local.session.mount("https://", adapter)
    return thread_local.session


class FastIPSpoofer:
    _IP_POOL = []
    _IP_INDEX = 0
    _IP_LOCK = threading.Lock()

    @classmethod
    def init_ip_pool(cls, count=500):
        if cls._IP_POOL:
            return
        prefixes = list(range(1, 224))
        cls._IP_POOL = []
        for a in prefixes:
            for _ in range(count // len(prefixes)):
                b = random.randint(0, 255)
                c = random.randint(0, 255)
                d = random.randint(1, 254)
                if (a == 10 or (a == 172 and 16 <= b <= 31) or
                    (a == 192 and b == 168) or a == 127):
                    continue
                cls._IP_POOL.append(f"{a}.{b}.{c}.{d}")
                if len(cls._IP_POOL) >= count:
                    break
            if len(cls._IP_POOL) >= count:
                break
        random.shuffle(cls._IP_POOL)

    @classmethod
    def get_ip(cls):
        with cls._IP_LOCK:
            if not cls._IP_POOL:
                cls.init_ip_pool(500)
            ip = cls._IP_POOL[cls._IP_INDEX % len(cls._IP_POOL)]
            cls._IP_INDEX += 1
            return ip

ip_spoofer = FastIPSpoofer()


USER_AGENTS = [
    "GarenaMSDK/4.0.42(SM-A525F ;Android)",
    "GarenaMSDK/4.0.39(SM-A325M;Android 13;en;HK;)",
    "GarenaMSDK/4.0.38(Redmi Note 10;Android 12;en;ID;)",
    "GarenaMSDK/4.0.40(Poco X3;Android 11;en;SG;)",
    "GarenaMSDK/4.0.41(SM-S918B;Android 14;en;IN;)",
    "GarenaMSDK/4.0.42(OnePlus 11;Android 13;en;US;)",
    "GarenaMSDK/4.0.39(Xiaomi 13 Pro;Android 13;pt;BR;)",
    "GarenaMSDK/4.0.40(Pixel 7 Pro;Android 14;en;US;)",
    "GarenaMSDK/4.0.38(ASUS ROG Phone 7;Android 13;id;ID;)",
    "GarenaMSDK/4.0.41(Infinix Note 12;Android 12;th;TH;)",
    "GarenaMSDK/4.0.43(SM-G998B;Android 13;ar;EG;)",
    "GarenaMSDK/4.0.37(Redmi Note 11;Android 11;es;MX;)",
    "GarenaMSDK/4.0.40(Poco F5;Android 13;en;VN;)",
    "GarenaMSDK/4.0.42(Realme GT 3;Android 13;hi;IN;)",
    "GarenaMSDK/4.0.39(Vivo V27;Android 13;en;PH;)",
    "GarenaMSDK/4.0.41(OPPO Reno 10;Android 13;id;ID;)",
    "GarenaMSDK/4.0.38(Tecno Camon 20;Android 13;fr;FR;)",
    "GarenaMSDK/4.0.40(Huawei P50;Android 11;ar;SA;)",
    "GarenaMSDK/4.0.42(Lenovo Legion Y70;Android 12;zh;TW;)",
    "GarenaMSDK/4.0.39(Zuck Z5 Pro;Android 11;en;US;)",
    "GarenaMSDK/4.0.44(SM-S928B;Android 14;en;SG;)",
    "GarenaMSDK/4.0.42(Xiaomi 14;Android 14;id;ID;)",
    "GarenaMSDK/4.0.40(Poco X5 Pro;Android 12;en;MY;)",
    "GarenaMSDK/4.0.41(Oppo Find X5;Android 13;th;TH;)",
    "GarenaMSDK/4.0.39(Vivo X80;Android 12;vi;VN;)",
    "GarenaMSDK/4.0.43(Realme 11 Pro;Android 13;hi;IN;)",
    "GarenaMSDK/4.0.38(Infinix Zero 30;Android 13;ar;SA;)",
    "GarenaMSDK/4.0.40(Tecno Phantom V;Android 13;pt;BR;)",
    "GarenaMSDK/4.0.42(Samsung A54;Android 13;es;MX;)",
    "GarenaMSDK/4.0.39(Samsung A34;Android 13;en;PH;)",
]

for i in range(100):
    models = ["SM-A", "SM-G", "CPH", "V", "RMX"]
    model = random.choice(models) + str(random.randint(1000, 9999))
    version = random.choice(["11","12","13","14"])
    ua = f"GarenaMSDK/4.0.{random.randint(30,60)}({model};Android {version};en;ID;)"
    USER_AGENTS.append(ua)

def get_random_ua():
    return random.choice(USER_AGENTS)


def EnC_Vr(N):
    H = []
    while True:
        BesTo = N & 0x7F
        N >>= 7
        if N: BesTo |= 0x80
        H.append(BesTo)
        if not N: break
    return bytes(H)

def CrEaTe_VarianT(field_number, value):
    field_header = (field_number << 3) | 0
    return EnC_Vr(field_header) + EnC_Vr(value)

def CrEaTe_LenGTh(field_number, value):
    field_header = (field_number << 3) | 2
    encoded_value = value.encode() if isinstance(value, str) else value
    return EnC_Vr(field_header) + EnC_Vr(len(encoded_value)) + encoded_value

def CrEaTe_ProTo(fields):
    packet = bytearray()
    for field, value in fields.items():
        if isinstance(value, dict):
            nested_packet = CrEaTe_ProTo(value)
            packet.extend(CrEaTe_LenGTh(field, nested_packet))
        elif isinstance(value, int):
            packet.extend(CrEaTe_VarianT(field, value))
        elif isinstance(value, str) or isinstance(value, bytes):
            packet.extend(CrEaTe_LenGTh(field, value))
    return packet


def E_AEs(Pc):
    Z = bytes.fromhex(Pc)
    key_bytes = bytes([89,103,38,116,99,37,68,69,117,104,54,37,90,99,94,56])
    iv = bytes([54,111,121,90,68,114,50,50,69,51,121,99,104,106,77,37])
    K = AES.new(key_bytes, AES.MODE_CBC, iv)
    R = K.encrypt(pad(Z, AES.block_size))
    return bytes.fromhex(R.hex())

def encrypt_api(plain_text):
    plain_text = bytes.fromhex(plain_text)
    key_bytes = bytes([89,103,38,116,99,37,68,69,117,104,54,37,90,99,94,56])
    iv = bytes([54,111,121,90,68,114,50,50,69,51,121,99,104,106,77,37])
    cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
    cipher_text = cipher.encrypt(pad(plain_text, AES.block_size))
    return cipher_text.hex()


def generate_random_name(name_prefix):
    characters = string.ascii_uppercase + string.digits
    random_part = ''.join(secrets.choice(characters) for _ in range(6))
    return f"{name_prefix}{random_part}"

def generate_custom_password(password_prefix="XORA"):
    prefix = password_prefix.upper() if password_prefix else "XORA"
    prefix = prefix[:5]
    rand_part = "".join(secrets.choice("0123456789ABCDEF") for _ in range(16))
    return f"{prefix}_{rand_part}"


def count_same_digits(account_id):
    from collections import Counter
    aid = str(account_id)
    if not aid.isdigit():
        return 0, None
    analyzed = aid[1:] if len(aid) > 1 else aid
    dc = Counter(analyzed)
    if not dc:
        return 0, None
    mx = max(dc.values())
    most = None
    for d, c in dc.items():
        if c == mx:
            most = d
            break
    return mx, most

def get_rarity_info(account_id):
    if not account_id or account_id == "N/A":
        return "NORMAL", "", 0
    sc, md = count_same_digits(account_id)
    if sc >= 11:   return "SCARE", f"{md}x{sc}", 100
    elif sc >= 10: return "SCARSE", f"{md}x{sc}", 95
    elif sc >= 9:  return "MYTHICAL", f"{md}x{sc}", 90
    elif sc >= 8:  return "MYTICH", f"{md}x{sc}", 85
    elif sc >= 7:  return "LEGENDARY", f"{md}x{sc}", 70
    elif sc >= 6:  return "EPIC", f"{md}x{sc}", 55
    elif sc >= 5:  return "RARELG", f"{md}x{sc}", 40
    elif sc >= 4:  return "RARE", f"{md}x{sc}", 25
    elif sc >= 3:  return "JELEK", f"{md}x{sc}", 10
    else:          return "NORMAL", "", 5


def create_single_account(args):
    name_prefix, region, password_prefix = args
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = create_acc(region, name_prefix, password_prefix)
            if result and result.get('uid') and result.get('password'):
                record_success()
                return result
            time.sleep(1)
        except Exception:
            time.sleep(1)
    record_fail()
    return None

def create_acc(region, name_prefix, password_prefix="XORA"):
    password = generate_custom_password(password_prefix)
    session = get_session()
    ua = get_random_ua()
    fake_ip = ip_spoofer.get_ip()

    
    url = "https://100067.connect.garena.com/api/v2/oauth/guest:register"
    payload = {"app_id": 100067, "client_type": 2, "password": password, "source": 2}
    body_json = json.dumps(payload, separators=(",", ":"))
    signature = hmac.new(key, body_json.encode("utf-8"), hashlib.sha256).hexdigest()

    headers = {
        "User-Agent": ua,
        "Connection": "Keep-Alive",
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "Authorization": f"Signature {signature}",
        "Content-Type": "application/json; charset=utf-8",
        "Host": "100067.connect.garena.com",
        "X-Forwarded-For": fake_ip,
        "X-Real-IP": fake_ip,
    }

    try:
        response = session.post(url, headers=headers, data=body_json, timeout=15)
        resp_json = response.json()
        if "data" in resp_json and "uid" in resp_json["data"]:
            uid = resp_json["data"]["uid"]
            return token(uid, password, region, name_prefix, ua, fake_ip)
        elif resp_json.get('uid'):
            uid = resp_json.get('uid')
            return token(uid, password, region, name_prefix, ua, fake_ip)
        return None
    except Exception:
        return None

def token(uid, password, region, name_prefix, ua=None, fake_ip=None):
    if ua is None: ua = get_random_ua()
    if fake_ip is None: fake_ip = ip_spoofer.get_ip()
    session = get_session()
    url = "https://100067.connect.garena.com/oauth/guest/token/grant"
    headers = {
        "Accept-Encoding": "gzip",
        "Connection": "Keep-Alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": "100067.connect.garena.com",
        "User-Agent": ua,
        "X-Forwarded-For": fake_ip,
        "X-Real-IP": fake_ip,
    }
    body = {
        "uid": uid, "password": password,
        "response_type": "token", "client_type": "2",
        "client_secret": key, "client_id": "100067"
    }
    try:
        response = session.post(url, headers=headers, data=body, timeout=15)
        resp_json = response.json()
        open_id = resp_json.get('open_id')
        access_token = resp_json.get("access_token")
        if not open_id or not access_token:
            return None
        result = encode_string(open_id)
        field = to_unicode_escaped(result['field_14'])
        field = codecs.decode(field, 'unicode_escape').encode('latin1')
        return Major_Regsiter(access_token, open_id, field, uid, password, region, name_prefix, ua, fake_ip)
    except Exception:
        return None

def encode_string(original):
    keystream = [0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30]
    encoded = ""
    for i in range(len(original)):
        encoded += chr(ord(original[i]) ^ keystream[i % len(keystream)])
    return {"open_id": original, "field_14": encoded}

def to_unicode_escaped(s):
    return ''.join(c if 32 <= ord(c) <= 126 else f'\\u{ord(c):04x}' for c in s)

def Major_Regsiter(access_token, open_id, field, uid, password, region, name_prefix, ua=None, fake_ip=None):
    if ua is None: ua = get_random_ua()
    if fake_ip is None: fake_ip = ip_spoofer.get_ip()
    session = get_session()
    if region.upper() in ["ME", "TH"]:
        url = "https://loginbp.common.ggbluefox.com/MajorRegister"
    else:
        url = "https://loginbp.ggblueshark.com/MajorRegister"
    internal_name = generate_random_name(name_prefix)
    headers = {
        "Accept-Encoding": "gzip",
        "Authorization": "Bearer",
        "Connection": "Keep-Alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "Expect": "100-continue",
        "ReleaseVersion": "OB54",
        "User-Agent": ua,
        "X-GA": "v1 1",
        "X-Unity-Version": "2021.3.15f1",
        "X-Forwarded-For": fake_ip,
        "X-Real-IP": fake_ip,
    }
    lang_code = get_region(region) or "en"
    payload = {
        1: internal_name, 2: access_token, 3: open_id,
        5: 102000007, 6: 4, 7: 1, 13: 1, 14: field,
        15: lang_code, 16: 1, 17: 1
    }
    try:
        payload_hex = CrEaTe_ProTo(payload).hex()
        payload_enc = E_AEs(payload_hex).hex()
        body = bytes.fromhex(payload_enc)
        response = session.post(url, headers=headers, data=body, verify=False, timeout=15)
        return login(uid, password, access_token, open_id, response.content.hex(),
                     response.status_code, internal_name, region, ua, fake_ip)
    except Exception:
        return None

def login(uid, password, access_token, open_id, response_hex, status_code, name, region, ua=None, fake_ip=None):
    if ua is None: ua = get_random_ua()
    if fake_ip is None: fake_ip = ip_spoofer.get_ip()
    lang = get_region(region) or "en"
    lang_b = lang.encode("ascii")
    headers = {
        "Accept-Encoding": "gzip",
        "Authorization": "Bearer",
        "Connection": "Keep-Alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "Expect": "100-continue",
        "ReleaseVersion": "OB54",
        "User-Agent": ua,
        "X-GA": "v1 1",
        "X-Unity-Version": "2021.3.15f1",
        "X-Forwarded-For": fake_ip,
        "X-Real-IP": fake_ip,
    }
    payload = b'\x1a\x132025-08-30 05:19:21"\tfree fire(\x01:\x081.114.13B2Android OS 9 / API-28 (PI/rel.cjw.20220518.114133)J\x08HandheldR\nATM MobilsZ\x04WIFI`\xb6\nh\xee\x05r\x03300z\x1fARMv7 VFPv3 NEON VMH | 2400 | 2\x80\x01\xc9\x0f\x8a\x01\x0fAdreno (TM) 640\x92\x01\rOpenGL ES 3.2\x9a\x01+Google|dfa4ab4b-9dc4-454e-8065-e70c733fa53f\xa2\x01\x0e105.235.139.91\xaa\x01\x02' + lang_b + b'\xb2\x01 1d8ec0240ede109973f3321b9354b44d\xba\x01\x014\xc2\x01\x08Handheld\xca\x01\x10Asus ASUS_I005DA\xea\x01@afcfbf13334be42036e4f742c80b956344bed760ac91b3aff9b607a610ab4390\xf0\x01\x01\xca\x02\nATM Mobils\xd2\x02\x04WIFI\xca\x03 7428b253defc164018c604a1ebbfebdf\xe0\x03\xa8\x81\x02\xe8\x03\xf6\xe5\x01\xf0\x03\xaf\x13\xf8\x03\x84\x07\x80\x04\xe7\xf0\x01\x88\x04\xa8\x81\x02\x90\x04\xe7\xf0\x01\x98\x04\xa8\x81\x02\xc8\x04\x01\xd2\x04=/data/app/com.dts.freefireth-PdeDnOilCSFn37p1AH_FLg==/lib/arm\xe0\x04\x01\xea\x04_2087f61c19f57f2af4e7feff0b24d9d9|/data/app/com.dts.freefireth-PdeDnOilCSFn37p1AH_FLg==/base.apk\xf0\x04\x03\xf8\x04\x01\x8a\x05\x0232\x9a\x05\n2019118692\xb2\x05\tOpenGLES2\xb8\x05\xff\x7f\xc0\x05\x04\xe0\x05\xf3F\xea\x05\x07android\xf2\x05pKqsHT5ZLWrYljNb5Vqh//yFRlaPHSO9NWSQsVvOmdhEEn7W+VHNUK+Q+fduA3ptNrGB0Ll0LRz3WW0jOwesLj6aiU7sZ40p8BfUE/FI/jzSTwRe2\xf8\x05\xfb\xe4\x06\x88\x06\x01\x90\x06\x01\x9a\x06\x014\xa2\x06\x014\xb2\x06"GQ@O\x00\x0e^\x00D\x06UA\x0ePM\r\x13hZ\x07T\x06\x0cm\\V\x0ejYV;\x0bU5'
    data = payload
    try:
        data = data.replace(b'afcfbf13334be42036e4f742c80b956344bed760ac91b3aff9b607a610ab4390', access_token.encode())
        data = data.replace(b'1d8ec0240ede109973f3321b9354b44d', open_id.encode())
    except Exception:
        pass
    d = encrypt_api(data.hex())
    Final_Payload = bytes.fromhex(d)
    if region.lower() in ["me", "th"]:
        URL = "https://loginbp.common.ggbluefox.com/MajorLogin"
    else:
        URL = "https://loginbp.ggblueshark.com/MajorLogin"
    try:
        session = get_session()
        RESPONSE = session.post(URL, headers=headers, data=Final_Payload, verify=False, timeout=15)
    except Exception:
        return None
    if RESPONSE.status_code == 200:
        if len(RESPONSE.text) < 10:
            return None
        try:
            start_idx = RESPONSE.text.find("eyJhbGci")
            if start_idx != -1:
                BASE64_TOKEN = RESPONSE.text[start_idx:]
                BASE64_TOKEN = re.split(r'[\s"\\]', BASE64_TOKEN.strip())[0]
                first_dot = BASE64_TOKEN.find(".")
                if first_dot != -1:
                    second_dot = BASE64_TOKEN.find(".", first_dot + 1)
                    if second_dot != -1:
                        JWT_TOKEN = BASE64_TOKEN[:second_dot + 44]

                        # Extract account_id from JWT
                        account_id = None
                        try:
                            parts = JWT_TOKEN.split(".")
                            pp = parts[1]
                            pp += '=' * ((4 - len(pp) % 4) % 4)
                            decoded = base64.urlsafe_b64decode(pp)
                            dd = json.loads(decoded)
                            account_id = dd.get('account_id') or dd.get('external_id')
                        except Exception:
                            pass

                        # Fallback via protobuf
                        if not account_id:
                            try:
                                jr = get_available_room(RESPONSE.content.hex())
                                pd = json.loads(jr) if jr else {}
                                account_id = pd.get('8', {}).get('data')
                                if isinstance(account_id, dict):
                                    account_id = account_id.get('data')
                            except Exception:
                                pass

                        return {
                            "uid": str(uid),
                            "account_id": str(account_id) if account_id else "N/A",
                            "password": password,
                            "name": name,
                            "region": region,
                            "status": "full_login",
                            "stage": "complete",
                            "jwt_token": JWT_TOKEN,
                            "access_token": access_token,
                            "open_id": open_id,
                        }
        except Exception:
            pass
    return None


def parse_results(parsed_results):
    result_dict = {}
    for result in parsed_results:
        field_data = {}
        field_data['wire_type'] = result.wire_type
        if result.wire_type in ("varint", "string", "bytes"):
            field_data['data'] = result.data
        elif result.wire_type == 'length_delimited':
            field_data["data"] = parse_results(result.data.results)
        result_dict[result.field] = field_data
    return result_dict

def get_available_room(input_text):
    try:
        parsed_results = Parser().parse(input_text)
        return json.dumps(parse_results(parsed_results))
    except Exception:
        return None


@app.route('/gen', methods=['GET'])
def generate_accounts():
    start_time = time.time()
    count = request.args.get('count', '1')

    try:
        count = int(count)
        count = max(1, min(count, 15))
    except Exception:
        count = 1

    name = FORCE_NAME_PREFIX
    region = FORCE_REGION
    pass_prefix = FORCE_PASS_PREFIX

    max_workers = 5
    results = []
    attempts = 0
    max_total_attempts = count * 10

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        while len(results) < count and attempts < max_total_attempts:
            needed = count - len(results)
            current_batch = min(needed, max_workers)
            futures = [
                executor.submit(create_single_account, (name, region, pass_prefix))
                for _ in range(current_batch)
            ]
            for future in concurrent.futures.as_completed(futures):
                attempts += 1
                result = future.result()
                if result and result.get('uid'):
                    aid = result.get('account_id', 'N/A')
                    rarity, reason, score = get_rarity_info(aid)
                    result['rarity'] = rarity
                    result['rarity_reason'] = reason
                    result['rarity_score'] = score
                    result['created_at'] = datetime.now().isoformat()
                    results.append(result)
                    print(f"[{len(results)}/{count}] UID {result['uid']} | ID {aid} | {rarity}")
                if len(results) >= count:
                    break
            if len(results) < count:
                time.sleep(1.5)

    elapsed = round(time.time() - start_time, 2)

    response_data = {
        "success": len(results) > 0,
        "total_requested": count,
        "total_created": len(results),
        "attempts_made": attempts,
        "elapsed_sec": elapsed,
        "workers": max_workers,
        "accounts": results,
        "forced_region": region,
        "forced_region_name": "INDONESIA",
        "forced_name_prefix": name,
        "password_prefix": pass_prefix,
    }

    
    if len(results) == 1:
        r = results[0]
        response_data.update({
            "uid": r.get('uid'),
            "password": r.get('password'),
            "name": r.get('name'),
            "region": r.get('region'),
            "account_id": r.get('account_id'),
            "jwt_token": r.get('jwt_token'),
            "access_token": r.get('access_token'),
            "open_id": r.get('open_id'),
        })
    elif len(results) > 1:
        
        r = results[0]
        response_data.update({
            "uid": r.get('uid'),
            "password": r.get('password'),
            "name": r.get('name'),
            "region": r.get('region'),
            "account_id": r.get('account_id'),
            "jwt_token": r.get('jwt_token'),
            "access_token": r.get('access_token'),
            "open_id": r.get('open_id'),
        })

    return jsonify(response_data)


@app.route('/')
def home():
    return jsonify({
        "message": "FreeFire Account Generator API - FULL LOGIN",
        "status": "active",
        "config": {
            "region": FORCE_REGION,
            "region_name": "INDONESIA",
            "name_prefix": FORCE_NAME_PREFIX,
            "password_prefix": FORCE_PASS_PREFIX,
        },
        "endpoint": "/gen?count=NUMBER",
        "max_count": 15,
        "example": "/gen?count=3",
    })


@app.route('/health')
def health():
    with STATS_LOCK:
        stats = dict(STATS)
    return jsonify({
        "status": "healthy",
        "stats": stats,
        "timestamp": datetime.now().isoformat(),
        "force_region": FORCE_REGION,
        "force_name_prefix": FORCE_NAME_PREFIX,
        "force_pass_prefix": FORCE_PASS_PREFIX,
    })


@app.route('/stats')
def stats_route():
    with STATS_LOCK:
        return jsonify(dict(STATS))


def application(environ, start_response):
    return app(environ, start_response)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=False, threaded=True)
