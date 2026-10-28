from pathlib import Path
import unicodedata

from fastapi import FastAPI, HTTPException

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CREATOR = "By Neexy"


def normalize_word(value: str) -> str:
    return unicodedata.normalize("NFC", value).strip().casefold()


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

                if not word or word.startswith("#"):
                    continue

                if all(
                    char.isalpha() or char in "-'’"
                    for char in word
                ):
                    words.add(word)

    return words


WORDS = load_words()

app = FastAPI(
    title="Kamus API",
    description="API pengecekan kata untuk permainan sambung kata",
    version="1.0.0"
)


@app.get("/")
def home():
    return {
        "nama": "Kamus API",
        "status": "aktif",
        "total_kata": len(WORDS),
        "creator": CREATOR
    }


@app.get("/api/kamus")
def check_word(text: str | None = None):
    if text is None or not text.strip():
        raise HTTPException(
            status_code=400,
            detail="Parameter text wajib diisi"
        )

    if len(text) > 100:
        raise HTTPException(
            status_code=400,
            detail="Panjang kata maksimal 100 karakter"
        )

    kata = normalize_word(text)

    if not kata:
        raise HTTPException(
            status_code=400,
            detail="Kata tidak boleh kosong"
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