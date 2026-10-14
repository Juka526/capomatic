"""Hand-written PDF bytes for tests: no PDF library builds the truth.

Pages are dicts: ``media`` box, optional ``crop``, ``rotate``, ``content``
(raw operators), ``extra`` (raw page-dict entries). Optional RC4-40 standard
security handler (PDF 1.7 spec, 7.6.3, algorithms 2-5, R2) for encrypted cases.
"""
import hashlib
import struct

_PAD = bytes.fromhex("28BF4E5E4E758A4164004E56FFFA01082E2E00B6D0683E802F0CA9FE6453697A")
_ID0 = bytes(range(16))
_P = -44


def _rc4(key: bytes, data: bytes) -> bytes:
    s = list(range(256))
    j = 0
    for i in range(256):
        j = (j + s[i] + key[i % len(key)]) % 256
        s[i], s[j] = s[j], s[i]
    out = bytearray()
    i = j = 0
    for byte in data:
        i = (i + 1) % 256
        j = (j + s[i]) % 256
        s[i], s[j] = s[j], s[i]
        out.append(byte ^ s[(s[i] + s[j]) % 256])
    return bytes(out)


def _padded(password: bytes) -> bytes:
    return (password + _PAD)[:32]


def _security(user: bytes, owner: bytes) -> tuple[bytes, bytes, bytes]:
    o = _rc4(hashlib.md5(_padded(owner)).digest()[:5], _padded(user))
    key = hashlib.md5(_padded(user) + o + struct.pack("<i", _P) + _ID0).digest()[:5]
    u = _rc4(key, _PAD)
    return key, o, u


def build_pdf(pages, *, catalog_extra=b"", encrypt=None, encrypt_key_name=b"/Encrypt",
              extra_objects=()):
    """Return PDF bytes. ``encrypt=(user_pw, owner_pw)`` enables RC4-40."""
    objs: list[bytes] = []  # objs[i] is object number i + 1

    def add(body: bytes) -> int:
        objs.append(body)
        return len(objs)

    key = None
    if encrypt is not None:
        key, o, u = _security(*encrypt)

    def stream(num_hint: int, data: bytes) -> bytes:
        if key is not None:
            obj_key = hashlib.md5(key + num_hint.to_bytes(3, "little") + b"\0\0").digest()[:10]
            data = _rc4(obj_key, data)
        return b"<< /Length %d >>\nstream\n" % len(data) + data + b"\nendstream"

    catalog = add(b"")
    tree = add(b"")
    kids = []
    for page in pages:
        content_ref = b""
        if page.get("content") is not None:
            num = len(objs) + 1
            add(stream(num, page["content"]))
            content_ref = b" /Contents %d 0 R" % num
        box = lambda b: b"[" + b" ".join(str(v).encode() for v in b) + b"]"
        body = b"<< /Type /Page /Parent %d 0 R /MediaBox " % tree + box(page["media"])
        if "crop" in page:
            body += b" /CropBox " + box(page["crop"])
        if "rotate" in page:
            body += b" /Rotate %d" % page["rotate"]
        body += content_ref + page.get("extra", b"") + b" >>"
        kids.append(add(body))
    for extra in extra_objects:
        add(extra)
    objs[catalog - 1] = b"<< /Type /Catalog /Pages %d 0 R" % tree + catalog_extra + b" >>"
    objs[tree - 1] = (b"<< /Type /Pages /Kids [" + b" ".join(b"%d 0 R" % k for k in kids)
                      + b"] /Count %d >>" % len(kids))
    enc_ref = b""
    if key is not None:
        enc = add(b"<< /Filter /Standard /V 1 /R 2 /O <" + o.hex().encode() + b"> /U <"
                  + u.hex().encode() + b"> /P %d >>" % _P)
        enc_ref = b" " + encrypt_key_name + b" %d 0 R" % enc

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += (b"trailer\n<< /Size %d /Root %d 0 R" % (len(objs) + 1, catalog) + enc_ref
            + b" /ID [<" + _ID0.hex().encode() + b"> <" + _ID0.hex().encode() + b">] >>\n"
            + b"startxref\n%d\n%%%%EOF\n" % xref)
    return bytes(out)


def fill(rgb, x, y, w, h) -> bytes:
    """Content operators filling one rectangle with an RGB colour (0-1 floats)."""
    r, g, b = rgb
    return b"%g %g %g rg %g %g %g %g re f\n" % (r, g, b, x, y, w, h)
