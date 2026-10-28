
import csv
import re
import unicodedata
from pathlib import Path
from urllib.request import Request, urlopen

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SOURCE_DIR = DATA_DIR / "source"
OUTPUT_FILE = DATA_DIR / "words.txt"

SOURCES = {
    "wordlist.txt": (
        "https://huggingface.co/datasets/"
        "Deddy/Indonesia-dataset-2023/resolve/main/"
        "dictionary/wordlist/data/wordlist.txt?download=true"
    ),
    "data.csv": (
        "https://huggingface.co/datasets/"
        "Lyon28/kamus-besar-bahasa-indonesia/"
        "resolve/main/data.csv?download=true"
    ),
}

TOKEN_PATTERN = re.compile(
    r"[^\W\d_]+(?:[-'’][^\W\d_]+)*",
    re.UNICODE
)

WORD_COLUMNS = {
    "key",
    "nama",
    "kata_dasar",
    "bentuk_tidak_baku",
    "kata_turunan",
}


def normalize_word(value: str) -> str:
    return unicodedata.normalize("NFC", value).strip().casefold()


def download_file(filename: str, url: str) -> Path:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    destination = SOURCE_DIR / filename

    if destination.exists() and destination.stat().st_size > 0:
        print(f"File sudah tersedia: {filename}")
        return destination

    print(f"Mengunduh {filename}...")

    request = Request(
        url,
        headers={"User-Agent": "KamusAPI/1.0"}
    )

    try:
        with urlopen(request, timeout=180) as response:
            with destination.open("wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
    except Exception:
        if destination.exists():
            destination.unlink()
        raise

    print(f"Selesai mengunduh: {filename}")
    return destination


def add_tokens(words: set[str], value: str) -> None:
    for token in TOKEN_PATTERN.findall(value):
        word = normalize_word(token)

        if word and all(
            char.isalpha() or char in "-'’"
            for char in word
        ):
            words.add(word)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    wordlist_path = download_file(
        "wordlist.txt",
        SOURCES["wordlist.txt"]
    )

    csv_path = download_file(
        "data.csv",
        SOURCES["data.csv"]
    )

    words: set[str] = set()

    print("Memproses wordlist...")

    with wordlist_path.open(
        "r",
        encoding="utf-8-sig",
        errors="replace"
    ) as file:
        for line in file:
            add_tokens(words, line)

    wordlist_total = len(words)
    print(f"Kata unik dari wordlist: {wordlist_total:,}")

    print("Memproses dataset CSV...")

    with csv_path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError("CSV tidak memiliki header.")

        available_columns = set(reader.fieldnames)
        selected_columns = WORD_COLUMNS & available_columns

        if "key" not in available_columns:
            raise ValueError(
                "Kolom 'key' tidak ditemukan pada dataset CSV. "
                f"Kolom tersedia: {reader.fieldnames}"
            )

        rows_processed = 0

        for row in reader:
            rows_processed += 1

            for column in selected_columns:
                value = row.get(column) or ""
                add_tokens(words, value)

    OUTPUT_FILE.write_text(
        "\n".join(sorted(words)) + "\n",
        encoding="utf-8"
    )

    added_words = len(words) - wordlist_total

    print("\n========== HASIL IMPOR ==========")
    print(f"Baris CSV diproses : {rows_processed:,}")
    print(f"Awal dari wordlist : {wordlist_total:,}")
    print(f"Kata unik tambahan : {added_words:,}")
    print(f"TOTAL KATA UNIK    : {len(words):,}")
    print(f"File hasil         : {OUTPUT_FILE}")
    print("=================================")

    if len(words) > 108000:
        print("BERHASIL: Target lebih dari 108.000 kata tercapai.")
    else:
        print(
            "TARGET BELUM TERCAPAI: Periksa sumber dan hasil impor "
            "sebelum menambahkan dataset lain."
        )


if __name__ == "__main__":
    main()
