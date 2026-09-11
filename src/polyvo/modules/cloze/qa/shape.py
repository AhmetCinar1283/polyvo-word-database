"""
BICIM kapisi — sayilabilir olan her sey. Hepsi garanti edilebilir, hepsi
REDDEDER.

Bu kapi cevabi ayni zamanda NORMALLESTIRIR: sonraki kapilar artik "acaba
liste mi, acaba bos mu" diye sormaz, temiz bir yapiyla calisir.

Zorluk etiketi MODELDEN GELMEZ, biz verdik (`difficulty.BANDS`) — modelin
sirayi bozmasi bir bicim hatasidir ve reddedilir, cunku hangi cevabin hangi
zorluk oldugu depoda SABIT olmalidir.
"""

from __future__ import annotations

from polyvo.modules.cloze.difficulty import BANDS, OPTION_COUNT, QUESTION_COUNT


def _text(value) -> str:
    """Modelin dondurdugu degeri guvenli bir metne cevirir."""
    return value.strip() if isinstance(value, str) else ""


def check(parsed: dict | None) -> tuple[str | None, list[dict]]:
    """(red_sebebi, normallestirilmis_sorular) dondurur."""
    if not isinstance(parsed, dict):
        return "cevap_json_degil", []

    raw = parsed.get("questions")
    if not isinstance(raw, list) or len(raw) != QUESTION_COUNT:
        return "soru_sayisi_uc_degil", []

    questions: list[dict] = []
    for seq, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            return "soru_nesne_degil", []

        band = BANDS[seq - 1]
        if _text(item.get("difficulty")).lower() != band.name:
            return "zorluk_etiketi_sirayla_uyusmuyor", []

        sentence = _text(item.get("sentence"))
        if not sentence:
            return "cumle_bos", []

        answer = _text(item.get("answer"))
        if not answer:
            return "dogru_cevap_bos", []

        raw_options = item.get("options")
        if not isinstance(raw_options, list) or len(raw_options) != OPTION_COUNT:
            return "sik_sayisi_dort_degil", []
        options = [_text(o) for o in raw_options]
        if any(not o for o in options):
            return "bos_sik", []
        if len({o.lower() for o in options}) != OPTION_COUNT:
            return "siklar_birbirinin_aynisi", []
        if answer.lower() not in {o.lower() for o in options}:
            return "dogru_cevap_siklar_arasinda_yok", []

        questions.append({
            "seq": seq,
            "difficulty": band.name,
            "sentence": sentence,
            "answer": answer,
            "options": options,
        })

    return None, questions
