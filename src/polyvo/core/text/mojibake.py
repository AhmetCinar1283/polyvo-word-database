"""
Mojibake onarimi: U+FFFD -> drop (geri alinamaz), cift-kodlama imzalari
(Ã/Å/Ä±) -> latin-1/utf-8 round-trip ile onarim.
"""

# Imzalar SAF ASCII kod noktasindan uretilir (`chr(...)`), karakterin
# KENDISI kaynak koduna gomulmez — aksi halde bir kodlama hatasinda dosyanin
# kendisi sessizce bozulup dedektoru koru edebilir.
_REPLACEMENT_CHAR = chr(0xFFFD)  # U+FFFD REPLACEMENT CHARACTER

# UTF-8 metnin latin-1 olarak okunmasinin imzalari: "Ã", "Å", "Ä±".
_DOUBLE_ENCODING_MARKERS = (chr(0xC3), chr(0xC5), chr(0xC4) + chr(0xB1))


def repair_text(text: str | None) -> tuple[str | None, bool]:
    """`(metin | None, degisti_mi)` doner. `None` = geri alinamaz bozuk
    (U+FFFD) — cagiran taraf dislamali. Cift-kodlama tespit edilirse
    latin-1/utf-8 round-trip ile onarim denenir."""
    if not text:
        return text, False
    if _REPLACEMENT_CHAR in text:
        return None, True
    if any(marker in text for marker in _DOUBLE_ENCODING_MARKERS):
        try:
            repaired = text.encode("latin-1").decode("utf-8")
        except (UnicodeDecodeError, UnicodeEncodeError):
            return text, False
        if repaired != text and _REPLACEMENT_CHAR not in repaired:
            return repaired, True
    return text, False
