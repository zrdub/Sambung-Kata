
from pathlib import Path
import re
import unicodedata

from fastapi import FastAPI, HTTPException, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CREATOR = "By Neexy"
MAX_TEXT_LENGTH = 100

WORD_PATTERN = re.compile(
    r"^[^\W\d_]+(?:[-'’][^\W\d_]+)*$",
    re.UNICODE
)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Kamus API",
    description="API pengecekan kata untuk permainan sambung kata",
    version="1.1.0"
)

app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler
)


def normalize_word(value: str) -> str:
    value = unicodedata.normalize("NFC", value).strip()
    value = value.casefold()
    return unicodedata.normalize("NFC", value)


def load_words() -> set[str]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    words = set()

    for file_path in DATA_DIR.glob("*.txt"):
        with file_path.open(
            "r",
            encoding="utf-8-sig",
            errors="replace"
        ) as file:
            for line in file:
                word = normalize_word(line)

                if WORD_PATTERN.fullmatch(word):
                    words.add(word)

    return words


WORDS = load_words()


@app.get("/")
def home():
    return {
        "nama": "Kamus API",
        "status": "aktif" if WORDS else "kamus_kosong",
        "total_kata": len(WORDS),
        "creator": CREATOR
    }


@app.get("/api/health")
def health():
    return {
        "status": "ok" if WORDS else "warning",
        "kamus_tersedia": bool(WORDS),
        "total_kata": len(WORDS)
    }


@app.get("/api/kamus")
@limiter.limit("60/minute")
def check_word(request: Request, text: str | None = None):
    if text is None or not text.strip():
        raise HTTPException(
            status_code=400,
            detail="Parameter text wajib diisi"
        )

    if len(text) > MAX_TEXT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail="Panjang kata maksimal 100 karakter"
        )

    kata = normalize_word(text)

    if not WORD_PATTERN.fullmatch(kata):
        raise HTTPException(
            status_code=400,
            detail="Masukkan satu kata tanpa spasi, angka, atau simbol lain"
        )

    hasil = "ADA" if kata in WORDS else "TIDAK ADA"

    return {
        "kata": text.strip(),
        "hasil": hasil,
        "creator": CREATOR
    }


@app.get("/api/stats")
def stats():
    return {
        "total_kata": len(WORDS),
        "creator": CREATOR
    }
