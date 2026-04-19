import pytest

# ==========================================
# 1. Mock 依赖项 (如果你在真实项目中，请删除这部分，使用真实的 import)
# ==========================================
class HttpProtocolException(Exception):
    pass

def text_(val):
    if isinstance(val, bytes):
        return val.decode('utf-8')
    return str(val)

AT = b'@'
COLON = b':'
SLASH = b'/'
DEFAULT_ALLOWED_URL_SCHEMES = [b'http', b'https']

# ==========================================
# 2. 待测源码 (这里贴入你的 Url 类源码)
# 为了脚本完整性，我保留了类的核心结构，运行时请确保类的代码在这。
# ==========================================
from typing import List, Tuple, Optional

class Url:
    def __init__(self, scheme=None, username=None, password=None, hostname=None, port=None, remainder=None):
        self.scheme = scheme
        self.username = username
        self.password = password
        self.hostname = hostname
        self.port = port
        self.remainder = remainder

    @classmethod
    def from_bytes(cls, raw: bytes, allowed_url_schemes: Optional[List[bytes]] = None) -> 'Url':
        # [此处省略源码内容，请将你提供的 Url.from_bytes 和 Url._parse 完整粘贴在这里]
        starts_with_single_slash = raw[0] == 47
        starts_with_double_slash = starts_with_single_slash and len(raw) >= 2 and raw[1] == 47
        if starts_with_single_slash and not starts_with_double_slash:
            return cls(remainder=raw)
        scheme = None
        rest = None
        if not starts_with_double_slash:
            parts = raw.split(b'://', 1)
            if len(parts) == 2:
                scheme = parts[0]
                rest = parts[1]
                if scheme not in (allowed_url_schemes or DEFAULT_ALLOWED_URL_SCHEMES):
                    raise HttpProtocolException('Invalid scheme received in the request line %r' % raw)
        else:
            rest = raw[len(SLASH + SLASH):]
        if scheme is not None or starts_with_double_slash:
            assert rest is not None
            parts = rest.split(SLASH, 1)
            username, password, host, port = Url._parse(parts[0])
            return cls(
                scheme=scheme if not starts_with_double_slash else b'http',
                username=username, password=password, hostname=host, port=port,
                remainder=None if len(parts) == 1 else (SLASH + parts[1]),
            )
        username, password, host, port = Url._parse(raw)
        return cls(username=username, password=password, hostname=host, port=port)

    @staticmethod
    def _parse(raw: bytes):
        split_at = raw.split(AT, 1)
        username, password = None, None
        if len(split_at) == 2:
            username, password = split_at[0].split(COLON)
        parts = split_at[-1].split(COLON, 2)
        num_parts = len(parts)
        port: Optional[int] = None
        if num_parts == 1:
            return username, password, parts[0], None
        if num_parts == 2:
            return username, password, COLON.join(parts[:-1]), int(parts[-1])
        try:
            last_token = parts[-1].split(COLON)
            port = int(last_token[-1])
            host = COLON.join(parts[:-1]) + COLON + COLON.join(last_token[:-1])
        except ValueError:
            host, port = raw, None
        rhost = host.decode('utf-8')
        if COLON.decode('utf-8') in rhost and rhost[0] != '[' and rhost[-1] != ']':
            host = b'[' + host + b']'
        return username, password, host, port

# ==========================================
# 3. pytest 测试用例
# ==========================================

# 正常解析的测试用例
@pytest.mark.parametrize("raw, allowed_schemes, expected", [
    (b"/path?query=1", None, {"scheme": None, "username": None, "password": None, "hostname": None, "port": None, "remainder": b"/path?query=1"}),
    (b"http://admin:123@localhost:8080/path", None, {"scheme": b"http", "username": b"admin", "password": b"123", "hostname": b"localhost", "port": 8080, "remainder": b"/path"}),
    (b"https://localhost", [b"https"], {"scheme": b"https", "username": None, "password": None, "hostname": b"localhost", "port": None, "remainder": None}),
    (b"//localhost/path", None, {"scheme": b"http", "username": None, "password": None, "hostname": b"localhost", "port": None, "remainder": b"/path"}),
    (b"localhost:443", None, {"scheme": None, "username": None, "password": None, "hostname": b"localhost", "port": 443, "remainder": None}),
    (b"http://::1:8080", None, {"scheme": b"http", "username": None, "password": None, "hostname": b"[::1]", "port": 8080, "remainder": None}),
    (b"http://a:b:c", None, {"scheme": b"http", "username": None, "password": None, "hostname": b"[a:b:c]", "port": None, "remainder": None}),
    (b"http://[a:b:c]", None, {"scheme": b"http", "username": None, "password": None, "hostname": b"[a:b:c]", "port": None, "remainder": None}),
])
def test_url_from_bytes_valid(raw, allowed_schemes, expected):
    url = Url.from_bytes(raw, allowed_schemes)
    assert url.scheme == expected["scheme"]
    assert url.username == expected["username"]
    assert url.password == expected["password"]
    assert url.hostname == expected["hostname"]
    assert url.port == expected["port"]
    assert url.remainder == expected["remainder"]

# 异常处理的测试用例
def test_url_from_bytes_invalid_scheme():
    with pytest.raises(HttpProtocolException):
        Url.from_bytes(b"ftp://localhost", [b"http", b"https"])

def test_url_from_bytes_missing_password():
    with pytest.raises(ValueError):
        # Python splits user/pass by COLON, missing COLON triggers unpacking ValueError
        Url.from_bytes(b"http://admin@localhost:8080")

def test_url_from_bytes_empty_string():
    with pytest.raises(IndexError):
        Url.from_bytes(b"")