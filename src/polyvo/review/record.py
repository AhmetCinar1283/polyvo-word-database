"""
Insan duzeltmesinin BICIMI — satir basina bir JSON nesnesi (JSONL).

Burada uygulanan uc kural:
  * `tier`/`source`/`status` DOSYADAN OKUNMAZ. Yedekte ne yazarsa yazsin
    ice aktarma sabitleri kullanir (`apply.py`) — yoksa bir metin dosyasi
    kendini "insan karari" ilan edip yazma kapisini kandirirdi.
  * BULUNMAYAN alan dokunulmaz. Insan yalnizca gloss'u duzeltmek icin
    ornekleri yeniden yazmak zorunda kalmaz.
  * BILINMEYEN alan sessizce yok sayilmaz, satiri dusurur: `gloss_tr` diye
    bir yazim hatasi "hicbir sey olmadi"la sonuclanmamalidir.

Is 3: `usage_note` artik `sense_usage_note`u adresler (kart sutununu DEGIL —
bkz. `targets.py`). Yeni `_l1` sonekli alanlar (`definition_l1`,
`usage_note_l1`, `examples_l1`, `gloss_note_l1`) cevrilmis icerigi tasir;
hangi alanin hangi tabloya gittigi `targets.FIELD_TARGETS`tedir.

Is 5: `cloze_rationale` (ipucu + sik basina aciklama) ve `cloze_rationale_l1`
(cevirisi) ayni sayi sozlesmesini (`QUESTION_COUNT`/`OPTION_COUNT`) kullanir
— ikinci bir kural kumesi yazilmaz. Bicim `cloze` alaninin ikizi: soru
basina bir ipucu, sik basina bir aciklama.

Is 6: `grammar` (cumle basina en cok `MAX_RULES_PER_SENTENCE` kurallik
paket) ve `grammar_l1` (notlarin cevirisi) `cloze_rationale` ile AYNI
`QUESTION_COUNT` sozlesmesini kullanir — grammar'in cumleleri BUGUN yalnizca
`cloze`dan geldigi icin (bkz. `apply.py`). `rule_id` biciminin (KATALOG
VARLIGI degil, yalnizca `EN.<ALAN>.<KURAL>` bicimi) kapisi BURADADIR;
katalogda GERCEKTEN var olup olmadigi `apply.py`de sorulur (o an katalog
elde, burada degil)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from polyvo.modules.cloze.difficulty import OPTION_COUNT, QUESTION_COUNT
from polyvo.modules.grammar.catalog import is_valid_id as grammar_is_valid_id
from polyvo.modules.grammar.model import (
    MAX_RULES_PER_SENTENCE,
    MIN_RULES_PER_SENTENCE,
)

#: Insanin degistirebilecegi alanlar. IPA ve seviye burada YOK: `item_phonetics`
#: tier sutunu tasimaz, yani yazma kapisi onu koruyamaz (v2).
EDITABLE_FIELDS: tuple[str, ...] = (
    "gloss_en", "register", "usage_note", "gloss_l1", "examples",
    "definition_l1", "usage_note_l1", "examples_l1", "gloss_note_l1",
    "cloze", "cloze_l1", "cloze_rationale", "cloze_rationale_l1",
    "grammar", "grammar_l1")

#: `null` yazilarak bosaltilabilen alanlar. Gloss'lar/tanimlar burada YOK —
#: onlarsiz kart/ceviri sevk edilemez, "bosalt" istegi bir duzeltme degil
#: bir kayiptir. Notlar KOSULLUDUR, bosaltmak GECERLI bir duzeltmedir.
NULLABLE_FIELDS: frozenset[str] = frozenset({
    "register", "usage_note", "usage_note_l1", "gloss_note_l1"})

#: Dosyada bulunabilen ama KARARA GIRMEYEN alanlar (export baglam icin yazar,
#: yedek zaman damgasi ekler). Varliklari hata degildir; degerleri okunmaz.
IGNORED_FIELDS: frozenset[str] = frozenset({
    "tier", "source", "model", "status", "reject_reason",
    "item_id", "sense_id", "headword", "pos", "updated_at", "saved_at"})

KEY_FIELD = "stable_key"

#: Bir GUVEN alani degil, bir ADRES alani: `gloss_l1`in hangi dile ait oldugu.
#: Yedekte tasinir ki karisik dilli bir yedek geri oynatilabilsin.
L1_FIELD = "l1"


@dataclass
class Correction:
    """Tek bir satirin duzeltmesi: anahtar + yalnizca VERILEN alanlar."""

    stable_key: str
    values: dict[str, object] = field(default_factory=dict)
    #: Dosyada bulunup okunmayan alanlar — rapora girsin diye tutulur.
    ignored: tuple[str, ...] = ()
    #: `gloss_l1`in dili (yalnizca adres; verilmezse cagiranin dili kullanilir).
    l1: str | None = None

    def to_json(self, **extra) -> str:
        """Yedege/dosyaya yazilacak tek satirlik JSON."""
        row = {KEY_FIELD: self.stable_key, **self.values, **extra}
        return json.dumps(row, ensure_ascii=False, sort_keys=True)


def _check_cloze(value: object) -> str | None:
    """Insanin yazdigi cloze paketini dogrular.

    Sayilar `modules/cloze/difficulty.py`den gelir — insan yolu ile model
    yolu AYNI sozlesmeyi kullanir, ikinci bir kural kumesi yazilmaz. Zorluk
    ETIKETI beklenmez: hangi sirada hangi zorluk oldugu sabittir, `apply.py`
    onu siradan turetir."""
    if not isinstance(value, list) or len(value) != QUESTION_COUNT:
        return "cloze_soru_sayisi_uc_degil"
    for item in value:
        if not isinstance(item, dict):
            return "cloze_soru_nesne_degil"
        for name in ("sentence", "answer"):
            text = item.get(name)
            if not isinstance(text, str) or not text.strip():
                return f"cloze_{name}_bos"
        options = item.get("options")
        if not isinstance(options, list) or len(options) != OPTION_COUNT:
            return "cloze_sik_sayisi_dort_degil"
        if any(not isinstance(o, str) or not o.strip() for o in options):
            return "bos_cloze_sikki"
        if len({o.strip().lower() for o in options}) != OPTION_COUNT:
            return "cloze_siklari_birbirinin_aynisi"
        if item["answer"].strip().lower() not in {
                o.strip().lower() for o in options}:
            return "cloze_dogru_cevap_siklar_arasinda_yok"
    return None


def _check_cloze_rationale(value: object) -> str | None:
    """Insanin yazdigi ipucu/aciklama paketini dogrular.

    Sayilar `cloze` alaniyla AYNI sozlesmeden (`QUESTION_COUNT`/
    `OPTION_COUNT`) gelir; uzunluk bandi (`rationale/shape.py`) BURADA
    ZORLANMAZ — insan karari yazma kapisini her zaman gecer, yalnizca
    SAYILABILIR bicim burada denetlenir."""
    if not isinstance(value, list) or len(value) != QUESTION_COUNT:
        return "rationale_soru_sayisi_uc_degil"
    for item in value:
        if not isinstance(item, dict):
            return "rationale_soru_nesne_degil"
        hint = item.get("hint")
        if not isinstance(hint, str) or not hint.strip():
            return "rationale_ipucu_bos"
        reasons = item.get("reasons")
        if not isinstance(reasons, list) or len(reasons) != OPTION_COUNT:
            return "rationale_aciklama_sayisi_dort_degil"
        if any(not isinstance(r, str) or not r.strip() for r in reasons):
            return "bos_rationale_aciklamasi"
    return None


def _check_grammar_rule(rule: object) -> str | None:
    """Insanin yazdigi TEK grammar kural satirini dogrular.

    `rule_id` icin BURADA sorulan sey BICIM (`EN.<ALAN>.<KURAL>`); katalogda
    GERCEKTEN var olup olmadigi `apply.py`nin isidir (katalog kod icinde
    durur, burasi ona bakmaz)."""
    if not isinstance(rule, dict):
        return "grammar_kural_nesne_degil"
    rule_id = rule.get("rule_id")
    if not isinstance(rule_id, str) or not grammar_is_valid_id(rule_id):
        return "grammar_rule_id_bicimi_gecersiz"
    for name in ("trigger", "note"):
        text = rule.get(name)
        if not isinstance(text, str) or not text.strip():
            return f"grammar_{name}_bos"
    return None


def _check_grammar(value: object) -> str | None:
    """Insanin yazdigi grammar paketini dogrular.

    Cumle sayisi `cloze_rationale` ile AYNI sozlesmeden (`QUESTION_COUNT`)
    gelir: grammar'in cumleleri bugun yalnizca `cloze`dan gelir. `rank`
    1..N BOSLUKSUZ ve YINELEMESIZ olmali (Is 6 §10) — bu SAYILABILIR bicim
    kapisidir, `trigger`in cumlenin icinde olup olmadigi `apply.py`de
    (o an cumle metni elde) sorulur."""
    if not isinstance(value, list) or len(value) != QUESTION_COUNT:
        return "grammar_cumle_sayisi_uc_degil"
    for item in value:
        if not isinstance(item, dict):
            return "grammar_cumle_nesne_degil"
        rules = item.get("rules")
        if not isinstance(rules, list) or not (
                MIN_RULES_PER_SENTENCE <= len(rules) <= MAX_RULES_PER_SENTENCE):
            return "grammar_kural_sayisi_gecersiz"
        ranks = [rule.get("rank") if isinstance(rule, dict) else None
                for rule in rules]
        if ranks != list(range(1, len(rules) + 1)):
            return "grammar_rank_bosluklu_ya_da_yinelemeli"
        for rule in rules:
            problem = _check_grammar_rule(rule)
            if problem:
                return problem
    return None


def _check_grammar_l1(value: object) -> str | None:
    """Insanin yazdigi grammar not cevirisini dogrular.

    `rule_id`/`trigger` burada YOKTUR — ikisi de cevrilmez (Is 6 §18),
    yalnizca `rank` (hangi kural notunun cevirisi oldugunu ADRESLEMEK icin)
    ve cevrilen `note` verilir. Adreslenen `rank`in o cumlede GERCEKTEN var
    olup olmadigi `apply.py`de sorulur (o an Ingilizce paket elde)."""
    if not isinstance(value, list) or len(value) != QUESTION_COUNT:
        return "grammar_l1_cumle_sayisi_uc_degil"
    for item in value:
        if not isinstance(item, dict):
            return "grammar_l1_cumle_nesne_degil"
        rules = item.get("rules")
        if not isinstance(rules, list) or not rules:
            return "grammar_l1_kural_listesi_bos"
        for rule in rules:
            if not isinstance(rule, dict):
                return "grammar_l1_kural_nesne_degil"
            if not isinstance(rule.get("rank"), int) or rule["rank"] < 1:
                return "grammar_l1_rank_gecersiz"
            note = rule.get("note")
            if not isinstance(note, str) or not note.strip():
                return "grammar_l1_note_bos"
    return None


def _check_value(field_name: str, value: object) -> str | None:
    """Bir alanin degerini dogrular; sorun varsa sebebini doner."""
    if value is None:
        if field_name in NULLABLE_FIELDS:
            return None
        return f"{field_name}_bos_birakilamaz"
    if field_name == "cloze":
        return _check_cloze(value)
    if field_name in ("cloze_rationale", "cloze_rationale_l1"):
        return _check_cloze_rationale(value)
    if field_name == "grammar":
        return _check_grammar(value)
    if field_name == "grammar_l1":
        return _check_grammar_l1(value)
    if field_name == "cloze_l1":
        if not isinstance(value, list) or len(value) != QUESTION_COUNT:
            return "cloze_ceviri_sayisi_uc_degil"
        for item in value:
            if not isinstance(item, str) or not item.strip():
                return "bos_cloze_ceviri_cumlesi"
        return None
    if field_name in ("examples", "examples_l1"):
        if not isinstance(value, list) or not value:
            return "ornekler_liste_degil_ya_da_bos"
        for item in value:
            if not isinstance(item, str) or not item.strip():
                return "bos_ornek_cumle"
        return None
    if not isinstance(value, str):
        return f"{field_name}_metin_degil"
    if not value.strip():
        return f"{field_name}_bos"
    return None


def parse_line(line: str) -> tuple[Correction | None, str | None]:
    """Bir JSONL satirini `Correction`a cevirir; (kayit, sorun) doner."""
    text = line.strip()
    if not text or text.startswith("#"):
        return None, None                      # bos satir/yorum: sessizce atlanir
    try:
        row = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, f"json_okunamadi: {exc.msg}"
    if not isinstance(row, dict):
        return None, "satir_bir_nesne_degil"

    key = row.get(KEY_FIELD)
    if not isinstance(key, str) or not key.strip():
        return None, f"{KEY_FIELD}_yok"

    l1 = row.get(L1_FIELD)
    if l1 is not None and (not isinstance(l1, str) or not l1.strip()):
        return None, "l1_gecersiz"

    values: dict[str, object] = {}
    ignored: list[str] = []
    for name, value in row.items():
        if name in (KEY_FIELD, L1_FIELD):
            continue
        if name in IGNORED_FIELDS:
            ignored.append(name)               # okunmaz — tier/source sabittir
            continue
        if name not in EDITABLE_FIELDS:
            return None, f"bilinmeyen_alan: {name}"
        problem = _check_value(name, value)
        if problem:
            return None, problem
        if name in ("examples", "examples_l1", "cloze_l1"):
            values[name] = [v.strip() for v in value]
        elif name in ("cloze", "cloze_rationale", "cloze_rationale_l1",
                      "grammar", "grammar_l1"):
            values[name] = value
        else:
            values[name] = value.strip() if isinstance(value, str) else value

    if not values:
        return None, "duzeltilecek_alan_yok"
    return Correction(key.strip(), values, tuple(sorted(ignored)),
                      l1.strip() if isinstance(l1, str) else None), None


def parse_file(path: str) -> tuple[list[Correction], list[str]]:
    """Bir JSONL dosyasini bastan sona okur; (kayitlar, sorunlar) doner."""
    corrections: list[Correction] = []
    problems: list[str] = []
    with open(path, encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, start=1):
            correction, problem = parse_line(line)
            if problem:
                problems.append(f"satir {lineno}: {problem}")
            elif correction is not None:
                corrections.append(correction)
    return corrections, problems
