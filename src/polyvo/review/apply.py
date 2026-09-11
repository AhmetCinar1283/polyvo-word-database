"""
Duzeltmelerin depoya YAZILDIGI tek yer.

Iki soz verir:
  1. `tier=0` ve `source="human"` BURADA sabittir; dosyadan okunmaz.
  2. Sorunlu tek satir varsa HICBIR SATIR yazilmaz — dogrulama tam bitmeden
     ilk `execute` bile calismaz (`delivery/gate.py` ile ayni disiplin).

Yazma izni yine `core/jobs/store/policy.py`den sorulur. Insan karari kapiyi
her zaman gecer; kapinin BURADA da cagrilmasi, ikinci bir kural kumesi
olmadigini garanti eder.

Is 3: hangi alanin hangi tabloya gittigi `targets.py`dendir — bu dosya
tablo bilgisi TASIMAZ, yalnizca haritayi okur ve yazar.

Is 4: cloze AYRI BIR DOSYADA yasar (`data/stores/cloze.sqlite`). Ikinci bir
transaction acmak yerine dosya ATTACH edilir; boylece "sorunlu tek satirda
hicbir satir yazilmaz" sozu IKI dosyada birden gecerli kalir (SQLite coklu
veritabani transaction'i).

Is 5: `cloze_rationale`/`cloze_rationale_l1` AYNI ATTACH'i kullanir (ayni
dosya, cloze'un ustune yazan tablolar). `question_sha256`/`rationale_sha256`
insanin yazdigi satirda da O ANKI veriden yeniden hesaplanir — insan
duzeltmesi BAYAT dogmaz (§17).

Is 6: `grammar`/`grammar_l1` KENDI dosyasina yazar (`data/stores/
grammar.sqlite`, `grammar` olarak ATTACH edilir). Grammar'in cumleleri
BUGUN yalnizca `cloze`dan geldigi icin (`owner="cloze"` BURADA SABIT
varsayilir — `review/` zaten cloze'a dogrudan bagli bir katmandir, grammar
uretim hattinin "hicbir kardesi tanimaz" sozu BURAYA UYGULANMAZ) `trigger`in
cumlede gecip gecmedigi de `cloze.sense_cloze_question`den okunarak burada
dogrulanir — model yolunun en guclu kapisi (`qa/trigger.py`) insan yolunda
da GEVSETILMEZ. `rule_id`in KATALOGDA gercekten var olup olmadigi da
burada sorulur (bicim kapisi `record.py`dedir, varlik kapisi burada)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from polyvo.core.jobs.store import policy
from polyvo.core.llm.quality import rank_for
from polyvo.modules.cloze import difficulty as cloze_difficulty
from polyvo.modules.cloze import schema as cloze_schema
from polyvo.modules.cloze.rationale import fingerprint as rationale_fingerprint
from polyvo.modules.grammar import catalog as grammar_catalog
from polyvo.modules.grammar import fingerprint as grammar_fingerprint
from polyvo.modules.grammar import schema as grammar_schema
from polyvo.modules.lexicon_card import schema as lexicon_schema
from polyvo.review import backup as backup_mod
from polyvo.review import record, targets

#: Insan satirinin degismez kimligi — dosyadan OKUNMAZ.
HUMAN_TIER = policy.TIER_HUMAN
HUMAN_SOURCE = "human"
HUMAN_STATUS = "approved"

#: `--l1` GEREKTIREN alanlar — biri bile korrekte varsa dil verilmek zorunda.
PER_L1_FIELDS = frozenset(
    name for name, t in targets.FIELD_TARGETS.items() if t.per_l1)


class ReviewError(RuntimeError):
    """Ice aktarma dogrulamayi gecemedi — hicbir satir yazilmadi."""


@dataclass
class Problem:
    """Bir satirin neden yazilamadigi."""
    stable_key: str
    reason: str


@dataclass
class ApplyResult:
    """Bir `import`/`restore` kosusunun sonucu."""
    applied: int = 0
    skipped_unknown: int = 0
    ignored_fields: int = 0
    #: Yazildiktan sonra hala 'approved' olmayan kartlar (sevkiyata girmezler).
    still_unapproved: list[str] = field(default_factory=list)
    backup_path: str | None = None


def _index(conn) -> dict[str, tuple[int, int, int, str, str | None]]:
    """`stable_key -> (sense_id, item_id, tier, status, model)`, TEK sorgu."""
    return {row[0]: (row[1], row[2], row[3], row[4], row[5]) for row in conn.execute(
        "SELECT stable_key, sense_id, item_id, tier, status, model FROM sense_cards")}


def _write_card_fields(conn, sense_id: int, values: dict) -> None:
    """`sense_cards`a DOGRUDAN dokunan alanlari tek UPDATE'te yazar."""
    card = {name: values[name] for name in targets.CARD_FIELDS if name in values}
    if not card:
        return
    columns = ", ".join(f"{name} = ?" for name in card)
    conn.execute(
        f"UPDATE sense_cards SET {columns}, tier = ?, status = ?,"
        " reject_reason = NULL, source = ?, model = NULL,"
        " updated_at = CURRENT_TIMESTAMP WHERE sense_id = ?",
        [*card.values(), HUMAN_TIER, HUMAN_STATUS, HUMAN_SOURCE, sense_id])


def _write_usage_note(conn, sense_id: int, values: dict) -> None:
    """`sense_usage_note`u yazar (Is 3: kartin parcasi DEGIL, kendi satiri)."""
    if "usage_note" not in values:
        return
    note = values["usage_note"] or ""
    conn.execute(
        "INSERT OR REPLACE INTO sense_usage_note (sense_id, note, reason,"
        " status, reject_reason, tier, source, model, prompt_hash, updated_at)"
        " VALUES (?,?,NULL,?,NULL,?,?,NULL,NULL,CURRENT_TIMESTAMP)",
        (sense_id, note, HUMAN_STATUS, HUMAN_TIER, HUMAN_SOURCE))


def _write_gloss_l1(conn, sense_id: int, l1: str | None, values: dict) -> None:
    """`sense_gloss_l1` (kelime karsiligi) ve isteqe bagli `gloss_note_l1`."""
    if "gloss_l1" in values:
        conn.execute(
            "INSERT OR REPLACE INTO sense_gloss_l1 (sense_id, l1, gloss, tier,"
            " source, model) VALUES (?,?,?,?,?,NULL)",
            (sense_id, l1, values["gloss_l1"], HUMAN_TIER, HUMAN_SOURCE))

    if "gloss_note_l1" in values:
        note = values["gloss_note_l1"]
        if note:
            conn.execute(
                "INSERT OR REPLACE INTO sense_gloss_l1_note (sense_id, l1,"
                " note, tier, source, model) VALUES (?,?,?,?,?,NULL)",
                (sense_id, l1, note, HUMAN_TIER, HUMAN_SOURCE))
        else:
            # `null` yazilarak bosaltilmis: not GECERLI sekilde kaldirilir.
            conn.execute(
                "DELETE FROM sense_gloss_l1_note WHERE sense_id = ? AND l1 = ?",
                (sense_id, l1))


def _write_examples(conn, sense_id: int, values: dict) -> None:
    """`sense_examples` — Ingilizce ornek cumleler."""
    if "examples" not in values:
        return
    # Once silinir: insanin 2 ornegi, modelin 3. ornegini oksuz birakmasin.
    conn.execute("DELETE FROM sense_examples WHERE sense_id = ?", (sense_id,))
    conn.executemany(
        "INSERT INTO sense_examples (sense_id, seq, text, tier, source)"
        " VALUES (?,?,?,?,?)",
        [(sense_id, seq, text, HUMAN_TIER, HUMAN_SOURCE)
         for seq, text in enumerate(values["examples"], start=1)])


def _write_translation(conn, sense_id: int, l1: str | None, values: dict) -> None:
    """`sense_translation`(+`_examples`) — Is 3 ceviri paketi.

    `definition_l1`/`usage_note_l1`den yalnizca VERILEN alan degisir: satirin
    diger sutunu once okunup korunur ("bulunmayan alan dokunulmaz" kurali
    burada SATIR ICI de gecerlidir)."""
    touches_row = "definition_l1" in values or "usage_note_l1" in values
    if touches_row:
        existing = conn.execute(
            "SELECT definition, usage_note FROM sense_translation"
            " WHERE sense_id = ? AND l1 = ?", (sense_id, l1)).fetchone()
        prev_definition = existing[0] if existing else None
        prev_note = existing[1] if existing else None
        definition = values.get("definition_l1", prev_definition)
        usage_note = values.get("usage_note_l1", prev_note)
        conn.execute(
            "INSERT OR REPLACE INTO sense_translation (sense_id, l1,"
            " definition, usage_note, status, reject_reason, tier, source,"
            " model, prompt_hash, updated_at)"
            " VALUES (?,?,?,?,?,NULL,?,?,NULL,NULL,CURRENT_TIMESTAMP)",
            (sense_id, l1, definition, usage_note, HUMAN_STATUS, HUMAN_TIER,
             HUMAN_SOURCE))

    if "examples_l1" in values:
        conn.execute(
            "DELETE FROM sense_translation_examples WHERE sense_id = ? AND l1 = ?",
            (sense_id, l1))
        conn.executemany(
            "INSERT INTO sense_translation_examples (sense_id, l1, seq, text,"
            " tier, source) VALUES (?,?,?,?,?,?)",
            [(sense_id, l1, seq, text, HUMAN_TIER, HUMAN_SOURCE)
             for seq, text in enumerate(values["examples_l1"], start=1)])


def _write_cloze(conn, sense_id: int, stable_key: str, values: dict) -> None:
    """`cloze.sense_cloze` (+ soru/sik) — insanin yazdigi uc soruluk paket.

    Zorluk etiketi dosyadan OKUNMAZ: hangi sirada hangi zorluk oldugu
    sabittir (`difficulty.BANDS`), siradan turetilir."""
    if "cloze" not in values:
        return
    conn.execute(
        "INSERT OR REPLACE INTO cloze.sense_cloze (sense_id, stable_key,"
        " status, reject_reason, warnings, tier, source, model, prompt_hash,"
        " updated_at) VALUES (?,?,?,NULL,NULL,?,?,NULL,NULL,CURRENT_TIMESTAMP)",
        (sense_id, stable_key, HUMAN_STATUS, HUMAN_TIER, HUMAN_SOURCE))
    conn.execute("DELETE FROM cloze.sense_cloze_question WHERE sense_id = ?",
                 (sense_id,))
    conn.execute("DELETE FROM cloze.sense_cloze_option WHERE sense_id = ?",
                 (sense_id,))
    for seq, question in enumerate(values["cloze"], start=1):
        answer = question["answer"].strip()
        conn.execute(
            "INSERT INTO cloze.sense_cloze_question (sense_id, seq, difficulty,"
            " sentence, answer, tier, source) VALUES (?,?,?,?,?,?,?)",
            (sense_id, seq, cloze_difficulty.band_for(seq).name,
             question["sentence"].strip(), answer, HUMAN_TIER, HUMAN_SOURCE))
        conn.executemany(
            "INSERT INTO cloze.sense_cloze_option (sense_id, seq, opt_seq,"
            " text, is_answer) VALUES (?,?,?,?,?)",
            [(sense_id, seq, opt_seq, text.strip(),
              1 if text.strip().lower() == answer.lower() else 0)
             for opt_seq, text in enumerate(question["options"], start=1)])


def _write_cloze_l1(conn, sense_id: int, l1: str | None, values: dict) -> None:
    """`cloze.sense_cloze_translation` (+ cumleler) — cevrilen CUMLELER.

    Siklar cevrilmez, bu yuzden burada siklara HIC dokunulmaz."""
    if "cloze_l1" not in values:
        return
    conn.execute(
        "INSERT OR REPLACE INTO cloze.sense_cloze_translation (sense_id, l1,"
        " status, reject_reason, warnings, tier, source, model, prompt_hash,"
        " updated_at) VALUES (?,?,?,NULL,NULL,?,?,NULL,NULL,CURRENT_TIMESTAMP)",
        (sense_id, l1, HUMAN_STATUS, HUMAN_TIER, HUMAN_SOURCE))
    conn.execute(
        "DELETE FROM cloze.sense_cloze_translation_sentence"
        " WHERE sense_id = ? AND l1 = ?", (sense_id, l1))
    conn.executemany(
        "INSERT INTO cloze.sense_cloze_translation_sentence (sense_id, l1,"
        " seq, sentence, tier, source) VALUES (?,?,?,?,?,?)",
        [(sense_id, l1, seq, sentence, HUMAN_TIER, HUMAN_SOURCE)
         for seq, sentence in enumerate(values["cloze_l1"], start=1)])


def _current_cloze_questions(conn, sense_id: int) -> list[dict]:
    """`cloze.sense_cloze_question`+`_option`den O ANKI soru+sik verisi.

    `rationale/fingerprint.py::question_sha256` bunun ustunde calisir."""
    options: dict[int, list[str]] = {}
    for seq, text in conn.execute(
            "SELECT seq, text FROM cloze.sense_cloze_option"
            " WHERE sense_id = ? ORDER BY seq, opt_seq", (sense_id,)):
        options.setdefault(seq, []).append(text)
    return [
        {"seq": seq, "sentence": sentence, "options": options.get(seq, [])}
        for seq, sentence in conn.execute(
            "SELECT seq, sentence FROM cloze.sense_cloze_question"
            " WHERE sense_id = ? ORDER BY seq", (sense_id,))
    ]


def _write_cloze_rationale(conn, sense_id: int, stable_key: str,
                           values: dict) -> None:
    """`cloze.sense_cloze_rationale` (+ ipucu/aciklama) — insanin yazdigi
    paket.

    `question_sha256` O ANKI sorulardan yeniden hesaplanir: insan
    duzeltmesi BAYAT dogmaz (Is 5 §17)."""
    if "cloze_rationale" not in values:
        return
    question_hash = rationale_fingerprint.question_sha256(
        _current_cloze_questions(conn, sense_id))
    conn.execute(
        "INSERT OR REPLACE INTO cloze.sense_cloze_rationale (sense_id,"
        " stable_key, status, reject_reason, warnings, tier, source, model,"
        " prompt_hash, question_sha256, updated_at)"
        " VALUES (?,?,?,NULL,NULL,?,?,NULL,NULL,?,CURRENT_TIMESTAMP)",
        (sense_id, stable_key, HUMAN_STATUS, HUMAN_TIER, HUMAN_SOURCE,
         question_hash))
    conn.execute("DELETE FROM cloze.sense_cloze_hint WHERE sense_id = ?",
                 (sense_id,))
    conn.execute(
        "DELETE FROM cloze.sense_cloze_option_reason WHERE sense_id = ?",
        (sense_id,))
    for seq, item in enumerate(values["cloze_rationale"], start=1):
        conn.execute(
            "INSERT INTO cloze.sense_cloze_hint (sense_id, seq, hint_seq,"
            " hint, tier, source) VALUES (?,?,1,?,?,?)",
            (sense_id, seq, item["hint"].strip(), HUMAN_TIER, HUMAN_SOURCE))
        conn.executemany(
            "INSERT INTO cloze.sense_cloze_option_reason (sense_id, seq,"
            " opt_seq, reason, tier, source) VALUES (?,?,?,?,?,?)",
            [(sense_id, seq, opt_seq, reason.strip(), HUMAN_TIER, HUMAN_SOURCE)
             for opt_seq, reason in enumerate(item["reasons"], start=1)])


def _write_cloze_rationale_l1(conn, sense_id: int, l1: str | None,
                              values: dict) -> None:
    """`cloze.sense_cloze_rationale_translation` (+ cevrilmis ipucu/aciklama).

    `rationale_sha256` O ANKI (bu transaction'da yazilmis olabilecek)
    Ingilizce ipucu/aciklamadan hesaplanir."""
    if "cloze_rationale_l1" not in values:
        return
    hints_now = [{"seq": seq, "hint": hint} for seq, hint in conn.execute(
        "SELECT seq, hint FROM cloze.sense_cloze_hint"
        " WHERE sense_id = ? AND hint_seq = 1 ORDER BY seq", (sense_id,))]
    reasons_now = [
        {"seq": seq, "opt_seq": opt_seq, "reason": reason}
        for seq, opt_seq, reason in conn.execute(
            "SELECT seq, opt_seq, reason FROM cloze.sense_cloze_option_reason"
            " WHERE sense_id = ? ORDER BY seq, opt_seq", (sense_id,))]
    rationale_hash = rationale_fingerprint.rationale_sha256(
        hints_now, reasons_now)

    conn.execute(
        "INSERT OR REPLACE INTO cloze.sense_cloze_rationale_translation"
        " (sense_id, l1, status, reject_reason, warnings, tier, source,"
        " model, prompt_hash, rationale_sha256, updated_at)"
        " VALUES (?,?,?,NULL,NULL,?,?,NULL,NULL,?,CURRENT_TIMESTAMP)",
        (sense_id, l1, HUMAN_STATUS, HUMAN_TIER, HUMAN_SOURCE, rationale_hash))
    conn.execute(
        "DELETE FROM cloze.sense_cloze_hint_l1 WHERE sense_id = ? AND l1 = ?",
        (sense_id, l1))
    conn.execute(
        "DELETE FROM cloze.sense_cloze_option_reason_l1"
        " WHERE sense_id = ? AND l1 = ?", (sense_id, l1))
    for seq, item in enumerate(values["cloze_rationale_l1"], start=1):
        conn.execute(
            "INSERT INTO cloze.sense_cloze_hint_l1 (sense_id, l1, seq,"
            " hint_seq, hint, tier, source) VALUES (?,?,?,1,?,?,?)",
            (sense_id, l1, seq, item["hint"].strip(), HUMAN_TIER,
             HUMAN_SOURCE))
        conn.executemany(
            "INSERT INTO cloze.sense_cloze_option_reason_l1 (sense_id, l1,"
            " seq, opt_seq, reason, tier, source) VALUES (?,?,?,?,?,?,?)",
            [(sense_id, l1, seq, opt_seq, reason.strip(), HUMAN_TIER,
              HUMAN_SOURCE)
             for opt_seq, reason in enumerate(item["reasons"], start=1)])


def _normalize_trigger(text: str) -> str:
    """`qa/trigger.py::_normalize`nin KUCUK bir kopyasi — insan yolu da
    AYNI toleransi (kucuk harf + tek bosluk) kullanir, baska hicbir
    esneklik tanimaz."""
    return re.sub(r"\s+", " ", text.strip().lower())


def _grammar_problem(conn, sense_id: int, stable_key: str,
                     values: dict) -> str | None:
    """`grammar`/`grammar_l1` icin YAZMADAN ONCE sorulan ek kapi.

    `trigger`in KENDI cumlesinde gecmesi ve `rule_id`nin KATALOGDA gercekten
    var olmasi burada dogrulanir (model yolunun AYNI iki kapisi); `grammar_l1`
    icin adreslenen `rank`in Ingilizce paketle uyusmasi da burada sorulur."""
    if "grammar" in values:
        sentences = _current_cloze_questions(conn, sense_id)
        if len(sentences) != len(values["grammar"]):
            return "grammar_cumle_sayisi_cloze_ile_uyusmuyor"
        for item, sentence in zip(values["grammar"], sentences):
            haystack = _normalize_trigger(sentence["sentence"])
            for rule in item["rules"]:
                if _normalize_trigger(rule["trigger"]) not in haystack:
                    return f"grammar_trigger_cumlede_yok: {stable_key}"
                if grammar_catalog.get(rule["rule_id"]) is None:
                    return f"grammar_rule_id_katalogda_yok: {rule['rule_id']}"

    if "grammar_l1" in values:
        if "grammar" in values:
            rank_sets = [{r["rank"] for r in item["rules"]}
                        for item in values["grammar"]]
        else:
            by_ref: dict[str, set] = {}
            for ref, rank in conn.execute(
                    "SELECT ref, rank FROM grammar.sentence_grammar_rule"
                    " WHERE owner = 'cloze' AND group_key = ?", (stable_key,)):
                by_ref.setdefault(ref, set()).add(rank)
            rank_sets = [by_ref.get(f"{stable_key}:{seq}", set())
                        for seq in range(1, len(values["grammar_l1"]) + 1)]
        if len(rank_sets) != len(values["grammar_l1"]):
            return "grammar_l1_cumle_sayisi_ingilizce_ile_uyusmuyor"
        for seq, (item, wanted_ranks) in enumerate(
                zip(values["grammar_l1"], rank_sets), start=1):
            addressed = {r["rank"] for r in item["rules"]}
            if not addressed <= wanted_ranks:
                return f"grammar_l1_rank_ingilizce_kuralla_uyusmuyor: {stable_key}:{seq}"
    return None


def _write_grammar(conn, sense_id: int, stable_key: str, values: dict) -> None:
    """`grammar.sentence_grammar` (+ `_rule`) — insanin yazdigi paket.

    `owner="cloze"` SABITTIR (bkz. modul docstring'i). `source_sha256`
    O ANKI cloze cumlelerinden yeniden hesaplanir: insan duzeltmesi BAYAT
    dogmaz (Is 6 §17, cloze/rationale ile AYNI disiplin)."""
    if "grammar" not in values:
        return
    sentences = _current_cloze_questions(conn, sense_id)
    source_hash = grammar_fingerprint.source_sha256(
        [s["sentence"] for s in sentences])
    conn.execute(
        "INSERT OR REPLACE INTO grammar.sentence_grammar (owner, group_key,"
        " status, reject_reason, warnings, tier, source, model, prompt_hash,"
        " source_sha256, updated_at)"
        " VALUES ('cloze',?,?,NULL,NULL,?,?,NULL,NULL,?,CURRENT_TIMESTAMP)",
        (stable_key, HUMAN_STATUS, HUMAN_TIER, HUMAN_SOURCE, source_hash))
    conn.execute(
        "DELETE FROM grammar.sentence_grammar_rule"
        " WHERE owner = 'cloze' AND group_key = ?", (stable_key,))
    for seq, item in enumerate(values["grammar"], start=1):
        ref = f"{stable_key}:{seq}"
        conn.executemany(
            "INSERT INTO grammar.sentence_grammar_rule (owner, group_key,"
            " ref, rank, rule_id, trigger, note, tier, source)"
            " VALUES ('cloze',?,?,?,?,?,?,?,?)",
            [(stable_key, ref, r["rank"], r["rule_id"], r["trigger"].strip(),
              r["note"].strip(), HUMAN_TIER, HUMAN_SOURCE)
             for r in item["rules"]])


def _write_grammar_l1(conn, stable_key: str, l1: str | None,
                      values: dict) -> None:
    """`grammar.sentence_grammar_translation` (+ `_rule_l1`) — cevrilmis
    notlar. `rule_id`/`trigger` BURADA HIC YOK — ikisi de cevrilmez."""
    if "grammar_l1" not in values:
        return
    rows = conn.execute(
        "SELECT ref, rank, note FROM grammar.sentence_grammar_rule"
        " WHERE owner = 'cloze' AND group_key = ?", (stable_key,)).fetchall()
    note_hash = grammar_fingerprint.note_sha256(
        [(ref, rank, note) for ref, rank, note in rows])
    conn.execute(
        "INSERT OR REPLACE INTO grammar.sentence_grammar_translation (owner,"
        " group_key, l1, status, reject_reason, warnings, tier, source,"
        " model, prompt_hash, note_sha256, updated_at)"
        " VALUES ('cloze',?,?,?,NULL,NULL,?,?,NULL,NULL,?,CURRENT_TIMESTAMP)",
        (stable_key, l1, HUMAN_STATUS, HUMAN_TIER, HUMAN_SOURCE, note_hash))
    conn.execute(
        "DELETE FROM grammar.sentence_grammar_rule_l1 WHERE owner = 'cloze'"
        " AND l1 = ? AND ref IN (SELECT ref FROM"
        " grammar.sentence_grammar_rule WHERE owner = 'cloze'"
        "  AND group_key = ?)", (l1, stable_key))
    for seq, item in enumerate(values["grammar_l1"], start=1):
        ref = f"{stable_key}:{seq}"
        conn.executemany(
            "INSERT INTO grammar.sentence_grammar_rule_l1 (owner, ref, rank,"
            " l1, note, tier, source) VALUES ('cloze',?,?,?,?,?,?)",
            [(ref, r["rank"], l1, r["note"].strip(), HUMAN_TIER, HUMAN_SOURCE)
             for r in item["rules"]])


def _needs_cloze(corrections: list[record.Correction]) -> bool:
    """Duzeltmelerden biri cloze deposuna dokunuyor mu (ATTACH gerekir mi).

    Grammar alanlari da `cloze` sart eder: `trigger`in dogrulanmasi icin
    O ANKI cloze cumlelerinin okunmasi gerekir (`_grammar_problem`)."""
    fields = targets.CLOZE_FIELDS | targets.GRAMMAR_FIELDS
    return any(name in fields
               for correction in corrections for name in correction.values)


def _needs_grammar(corrections: list[record.Correction]) -> bool:
    """Duzeltmelerden biri grammar deposuna dokunuyor mu (ATTACH gerekir mi)."""
    return any(name in targets.GRAMMAR_FIELDS
               for correction in corrections for name in correction.values)


def _write(conn, sense_id: int, correction: record.Correction,
           l1: str | None) -> None:
    """Kapidan gecmis tek bir duzeltmeyi yazar (transaction cagirana ait).

    Her alan ailesi KENDI tablosuna yazilir (`targets.py`) — bir alanin
    duzeltmesi baska bir ailenin tablosuna DOKUNMAZ."""
    values = correction.values
    _write_card_fields(conn, sense_id, values)
    _write_usage_note(conn, sense_id, values)
    _write_gloss_l1(conn, sense_id, l1, values)
    _write_examples(conn, sense_id, values)
    _write_translation(conn, sense_id, l1, values)
    _write_cloze(conn, sense_id, correction.stable_key, values)
    _write_cloze_l1(conn, sense_id, l1, values)
    _write_cloze_rationale(conn, sense_id, correction.stable_key, values)
    _write_cloze_rationale_l1(conn, sense_id, l1, values)
    _write_grammar(conn, sense_id, correction.stable_key, values)
    _write_grammar_l1(conn, correction.stable_key, l1, values)


def apply(corrections: list[record.Correction], *, l1: str | None,
          skip_unknown: bool = False, write_backup: bool = True,
          conn=None) -> ApplyResult:
    """Duzeltmeleri dogrular, kapidan gecirir ve TEK transaction'da yazar."""
    owned = conn is None
    conn = conn if conn is not None else lexicon_schema.open_lexicon_db()
    attached = False
    attached_grammar = False
    try:
        if _needs_cloze(corrections):
            # Once semanin varligi garanti edilir: var olmayan bir dosyayi
            # ATTACH etmek TABLOSUZ bos bir veritabani baglardi.
            cloze_schema.open_cloze_db().close()
            conn.execute("ATTACH DATABASE ? AS cloze",
                         (cloze_schema.cloze_db_path(),))
            attached = True
        if _needs_grammar(corrections):
            grammar_schema.open_grammar_db().close()
            conn.execute("ATTACH DATABASE ? AS grammar",
                         (grammar_schema.grammar_db_path(),))
            attached_grammar = True
        index = _index(conn)
        problems: list[Problem] = []
        planned: list[tuple[int, record.Correction, str | None]] = []
        skipped = 0

        for correction in corrections:
            found = index.get(correction.stable_key)
            if found is None:
                # Kimlik URETILMEZ: karsiligi olmayan anahtar duzeltilemez.
                if skip_unknown:
                    skipped += 1
                    continue
                problems.append(Problem(correction.stable_key, "depoda_yok"))
                continue

            sense_id, _item_id, tier, status, model = found
            row_l1 = correction.l1 or l1
            needs_l1 = any(name in correction.values for name in PER_L1_FIELDS)
            if needs_l1 and not row_l1:
                problems.append(Problem(correction.stable_key, "l1_verilmedi"))
                continue

            # Kapi burada KARTIN mevcut durumuna gore soruluyor — hangi
            # tabloya yazilirsa yazilsin insan karari (tier 0) HER ZAMAN
            # gecer (`policy.should_write` kural 2); bu cagri disiplin icin.
            decision = policy.should_write(
                policy.Existing(tier=tier, status=status, rank=rank_for(model)),
                new_tier=HUMAN_TIER, new_status=HUMAN_STATUS, new_rank=None)
            if not decision.write:            # insan karari icin olmamali
                problems.append(Problem(correction.stable_key,
                                        f"kapi_reddetti: {decision.reason}"))
                continue

            grammar_problem = _grammar_problem(
                conn, sense_id, correction.stable_key, correction.values)
            if grammar_problem:
                problems.append(Problem(correction.stable_key, grammar_problem))
                continue
            planned.append((sense_id, correction, row_l1))

        if problems:
            detail = "\n  ".join(f"{p.stable_key}: {p.reason}" for p in problems)
            raise ReviewError(f"{len(problems)} satir yazilamadi:\n  {detail}")

        with conn:                            # tek transaction: hep ya da hic
            for sense_id, correction, row_l1 in planned:
                _write(conn, sense_id, correction, row_l1)

        result = ApplyResult(
            applied=len(planned), skipped_unknown=skipped,
            ignored_fields=sum(len(c.ignored) for c in corrections))
        if planned:
            keys = [c.stable_key for _s, c, _l in planned]
            marks = ",".join("?" * len(keys))
            result.still_unapproved = sorted(
                row[0] for row in conn.execute(
                    f"SELECT stable_key FROM sense_cards WHERE status != ?"
                    f" AND stable_key IN ({marks})", [HUMAN_STATUS, *keys]))
        if write_backup and planned:
            result.backup_path = backup_mod.append(
                [c for _s, c, _l in planned], l1=l1)
        return result
    finally:
        if attached_grammar:
            conn.execute("DETACH DATABASE grammar")
        if attached:
            conn.execute("DETACH DATABASE cloze")
        if owned:
            conn.close()
