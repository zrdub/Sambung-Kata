
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SOURCE_DIR = DATA_DIR / "source"
WORDS_FILE = DATA_DIR / "words.txt"

SOURCE_URL = (
    "https://kaikki.org/idwiktionary/"
    "Bahasa%20Indonesia/"
    "kaikki.org-dictionary-BahasaIndonesia.jsonl"
)

SOURCE_FILE = SOURCE_DIR / "kaikki-indonesia.jsonl"

WORD_PATTERN = re.compile(
    r"[^\W\d_]+(?:[-'’][^\W\d_]+)*",
    re.UNICODE
)


def normalize_word(value: str) -> str:
    return unicodedata.normalize(
        "NFC",
        value.strip()
    ).casefold()


def add_word(words: set[str], value) -> bool:
    if not isinstance(value, str):
        return False

    word = normalize_word(value)

    if not WORD_PATTERN.fullmatch(word):
        return False

    old_size = len(words)
    words.add(word)
    return len(words) > old_size


def download_source() -> Path:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)

    if SOURCE_FILE.exists() and SOURCE_FILE.stat().st_size > 0:
        print("Menggunakan file sumber yang sudah diunduh.")
        return SOURCE_FILE

    temporary_file = SOURCE_FILE.with_suffix(".part")

    request = Request(
        SOURCE_URL,
        headers={"User-Agent": "KamusAPI/1.0"}
    )

    print("Mengunduh data kosakata dari Kaikki.org...")

    try:
        with urlopen(request, timeout=180) as response:
            with temporary_file.open("wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)

        temporary_file.replace(SOURCE_FILE)

    except Exception as error:
        if temporary_file.exists():
            temporary_file.unlink()

        raise RuntimeError(
            f"Gagal mengunduh sumber kosakata: {error}"
        ) from error

    print("Unduhan sumber selesai.")
    return SOURCE_FILE


def main():
    if not WORDS_FILE.exists():
        raise FileNotFoundError(
            "data/words.txt tidak ditemukan. "
            "Jalankan impor kamus awal terlebih dahulu."
        )

    words = set()

    with WORDS_FILE.open(
        "r",
        encoding="utf-8-sig"
    ) as file:
        for line in file:
            add_word(words, line)

    initial_total = len(words)
    print(f"Kata unik sebelum penambahan: {initial_total:,}")

    source_path = download_source()
    entries_processed = 0
    new_words = 0
    invalid_lines = 0

    print("Memproses data Wiktionary...")

    with source_path.open(
        "r",
        encoding="utf-8",
        errors="replace"
    ) as file:
        for line in file:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                invalid_lines += 1
                continue

            if not isinstance(entry, dict):
                continue

            language_code = entry.get("lang_code")

            if language_code and language_code != "id":
                continue

            entries_processed += 1

            candidates = [entry.get("word")]

            forms = entry.get("forms", [])

            if isinstance(forms, list):
                for form in forms:
                    if isinstance(form, dict):
                        candidates.append(form.get("form"))
                    elif isinstance(form, str):
                        candidates.append(form)

            for candidate in candidates:
                if add_word(words, candidate):
                    new_words += 1

    WORDS_FILE.write_text(
        "\n".join(sorted(words)) + "\n",
        encoding="utf-8"
    )

    attribution = f"""# Sumber Data Kosakata

- Sumber: Kaikki.org — Bahasa Indonesia machine-readable dictionary
- URL: https://kaikki.org/idwiktionary/Bahasa%20Indonesia/index.html
- Data diunduh: {datetime.now(timezone.utc).date().isoformat()}
- Lisensi sumber: mengikuti lisensi Wiktionary, termasuk CC BY-SA dan GFDL.
- Atribusi sumber wajib dipertahankan ketika mendistribusikan data turunannya.
- Data gabungan juga dapat berisi data dari sumber lain. Periksa lisensi
  setiap sumber sebelum mendistribusikan atau menggunakan untuk tujuan komersial.

Jumlah entri sumber yang diproses: {entries_processed}
Kata unik sebelum penambahan: {initial_total}
Kata baru yang ditambahkan: {new_words}
Jumlah kata unik akhir: {len(words)}
"""

    (BASE_DIR / "DATA_SOURCES.md").write_text(
        attribution,
        encoding="utf-8"
    )

    print("\n========== HASIL PENAMBAHAN ==========")
    print(f"Entri sumber diproses : {entries_processed:,}")
    print(f"Kata unik sebelumnya  : {initial_total:,}")
    print(f"Kata baru ditambahkan : {new_words:,}")
    print(f"TOTAL KATA UNIK       : {len(words):,}")
    print(f"Baris JSON rusak      : {invalid_lines:,}")
    print("File kamus            : data/words.txt")
    print("Catatan sumber         : DATA_SOURCES.md")
    print("======================================")

    if len(words) > 108000:
        print("BERHASIL: Target lebih dari 108.000 kata tercapai.")
    else:
        print(
            "Target belum tercapai. "
            "Perlu sumber tambahan yang sesuai."
        )


if __name__ == "__main__":
    main()
