"""
`workspace/en/mojibake_report.json`'in karar tablosunun calisma zamaninda
uygulanan hali: U+FFFD -> drop (bilgi kalici kaybolmus, geri alinamaz),
cift-kodlama imzalari (Ã / Å / Ä±) -> repair (`encode('latin-1').decode('utf-8')`).

F1'in polyvo_v2 uzerindeki taramasi sifir gercek mojibake dogruladi (bkz.
`workspace/en/mojibake_report.json`), yani bu build icin pratikte no-op —
ama gelecekte farkli bir build'de gercek vaka cikarsa sessizce atlanmasin
diye mantik burada kalici olarak duruyor (F2_LEARNING_ITEMS.md § 2.1 madde 2).
"""

# BOZUK KARAKTER (U+FFFD) HER ZAMAN KACIS DIZISIYLE YAZILIR — 2026-08-22.
#
# Bu satir bir zamanlar karakterin KENDISINI iceriyordu ve bir kodlama
# round-trip'inde SESSIZCE KAYBOLDU; geriye `if "" in text:` kaldi. Python'da
# bos dize HER dizenin icinde bulunur, yani kontrol her metin icin True
# donmeye basladi: `repair_text` bos olmayan HER metni "geri alinamaz bicimde
# bozuk" ilan etti. Olculen sonuc (2026-08-22, `stores/translation_store.sqlite`,
# 11.982 satir): 10.037 satir (%83,8) `mojibake_repaired` bayragi tasiyor,
# GERCEKTE U+FFFD iceren satir sayisi ise SIFIR. Dahasi gercek bir cift-kodlama
# vakasi da onarilamaz hale gelmisti — fonksiyon onarimi denemeden once
# `None` donuyordu, yani onarim mantigi tamamen olu koddu.
#
# Ders: mojibake DEDEKTORU, mojibake'e ugrayabilecek bir karakteri kaynak
# koduna gomerse kendi hastaligina yakalanir. Bu yuzden bu dosyadaki her
# imza SAF ASCII kod noktasindan uretilir (`chr(...)`) — bir daha ayni
# sekilde sessizce kaybolamaz, kaybolursa da `chr` cagrisi patlar.
_REPLACEMENT_CHAR = chr(0xFFFD)  # U+FFFD REPLACEMENT CHARACTER

# UTF-8 metnin latin-1 olarak okunmasinin imzalari: "Ã", "Å", "Ä±".
_DOUBLE_ENCODING_MARKERS = (chr(0xC3), chr(0xC5), chr(0xC4) + chr(0xB1))


def repair_text(text: str | None) -> tuple[str | None, bool]:
    """Donus: `(metin | None, degisti_mi)`.

    `None` donerse metin geri alinamaz bicimde bozuk demektir (U+FFFD) —
    cagiran taraf bu aday/oge'yi dislamali. Cift-kodlama imzasi tespit
    edilirse `latin-1 -> utf-8` round-trip ile onarim denenir; basarisiz
    olursa metin degistirilmeden doner."""
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
