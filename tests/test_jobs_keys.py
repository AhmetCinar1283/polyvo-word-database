"""
`core/jobs/keys.py` testleri: bilesik anahtar sozlesmesi.

Bos varyant bugunku davranisla BIREBIR ayni olmali (geriye donuk uyum);
dolu varyant ise ayni ham `stable_key`e sahip iki birimi motor icin
BIRBIRINDEN AYRI satirlar haline getirmeli — ikisi de birbirini ezmemeli ve
her biri kendi kapi kararini almali. Deneme gunlugune ham anahtarin gittigi
de burada dogrulanir.
"""

from __future__ import annotations

import pytest

from polyvo.core.jobs import keys, schema
from polyvo.core.jobs.base import Job, JobContext, QaResult, Unit
from polyvo.core.jobs.engine import run as engine_run
from polyvo.core.jobs.store.base import ArtifactStore, WriteRequest
from polyvo.core.jobs.store.policy import Existing
from polyvo.core.llm.base import LLMResult
from polyvo.core.llm.cache import open_llm_cache_db


# ── compose_key ─────────────────────────────────────────────────────────

def test_bos_varyant_ham_anahtarla_birebir_ayni():
    assert keys.compose_key("en:bank:noun", "") == "en:bank:noun"


def test_dolu_varyant_farkli_anahtar_uretir():
    kv = keys.compose_key("en:bank:noun", "es")
    assert kv != "en:bank:noun"


def test_farkli_varyantlar_farkli_anahtar_uretir():
    a = keys.compose_key("en:bank:noun", "es")
    b = keys.compose_key("en:bank:noun", "de")
    assert a != b


# ── with_variant ────────────────────────────────────────────────────────

def test_with_variant_bos_iken_unit_degismez():
    unit = Unit(key="en:bank:noun", name="bank (noun)", data={"headword": "bank"})
    out = keys.with_variant(unit, "")
    assert out is unit


def test_with_variant_dolu_iken_ham_anahtar_data_da_saklanir():
    unit = Unit(key="en:bank:noun", name="bank (noun)", data={"headword": "bank"})
    out = keys.with_variant(unit, "es")
    assert out.key == keys.compose_key("en:bank:noun", "es")
    assert out.data["stable_key"] == "en:bank:noun"
    assert out.data["headword"] == "bank"          # eski alanlar korunur
    assert "es" in out.name                        # rapor varyanti gostersin


# ── Motor seviyesi: iki varyant birbirini ezmez ──────────────────────────

class FakeProvider:
    """Agi olmayan sahte saglayici."""

    def __init__(self, label="local:test"):
        self.label = label
        self.name = "fake"
        self.model = label.split(":", 1)[-1]
        self.calls: list[str] = []

    def preflight(self):
        return None

    def peek_cached(self, prompt, cache_conn):
        """Onbellekteki cevabi cagri yapmadan doner; yoksa None."""
        from polyvo.core.llm.cache import get_cached, hash_prompt
        hit = get_cached(cache_conn, hash_prompt(self.label, prompt))
        if hit is None:
            return None
        return LLMResult({"text": hit}, True, hit)

    def complete_json(self, prompt, cache_conn, *, max_tokens, temperature,
                      pace_delay=0.0, bypass_cache=False):
        from polyvo.core.llm.cache import get_cached, hash_prompt, store_cached
        h = hash_prompt(self.label, prompt)
        hit = None if bypass_cache else get_cached(cache_conn, h)
        if hit is not None:
            return LLMResult({"text": hit}, True, hit)
        self.calls.append(prompt)
        store_cached(cache_conn, h, self.label, prompt, "tamam")
        return LLMResult({"text": "tamam"}, False, "tamam")


class MemoryStore(ArtifactStore):
    """Bellekte tutan en kucuk gercek depo."""

    def __init__(self):
        self.rows: dict[str, Existing] = {}

    def load_existing(self, ctx):
        return dict(self.rows)

    def _write_row(self, ctx, request: WriteRequest):
        self.rows[request.unit.key] = Existing(tier=request.tier,
                                               status=request.status,
                                               rank=request.rank)

    def commit(self):
        pass


class VariantJob(Job):
    """Tek ham stable_key'i, `ctx.variant`e gore bilesik anahtara tasir."""

    family, kind, command, prompt_version = "test", "variant-card", "test-variant", "v1"

    def load_units(self, ctx):
        raw = Unit(key="en:bank:noun", name="bank (noun)", data={})
        return [keys.with_variant(raw, ctx.variant)]

    def build_prompt(self, unit, retry_note=None):
        return "prompt"

    def run_qa(self, parsed, unit):
        return QaResult(True, None, {"ok": True})


@pytest.fixture
def conns(tmp_path):
    cache = open_llm_cache_db(str(tmp_path / "llm_cache.sqlite"))
    attempts = schema.open_attempts(str(tmp_path / "attempts.sqlite"))
    yield cache, attempts
    cache.close()
    attempts.close()


def go(job, store, provider, ctx, conns):
    cache, attempts = conns
    return engine_run.run(job, ctx, provider=provider, store=store,
                          cache_conn=cache, attempts_conn=attempts,
                          assume_yes=True)


def test_iki_varyant_ayri_satir_uretir_birbirini_ezmez(conns):
    store, provider = MemoryStore(), FakeProvider()
    go(VariantJob(), store, provider,
       JobContext(tag="t", l2="en", variant="es"), conns)
    go(VariantJob(), store, provider,
       JobContext(tag="t", l2="en", variant="de"), conns)

    assert set(store.rows) == {
        keys.compose_key("en:bank:noun", "es"),
        keys.compose_key("en:bank:noun", "de"),
    }
    assert len(store.rows) == 2


def test_bir_varyant_onayli_iken_digeri_hala_islenir(conns):
    """Ayni ham stable_key, farkli varyant — biri onayli olsa da digeri
    kendi kapi kararini alir, `skip_done` demez."""
    store, provider = MemoryStore(), FakeProvider()
    first = go(VariantJob(), store, provider,
              JobContext(tag="t", l2="en", variant="es"), conns)
    assert first.approved == 1

    second = go(VariantJob(), store, provider,
               JobContext(tag="t", l2="en", variant="de"), conns)
    # es'in onayi de'yi "skip_done" yapmaz — de kendi kapi kararini alir ve
    # islenir (ayni prompt oldugu icin onbellekten bedava doner, ama YINE DE
    # islenir; bu ikinci onbellek testi degil, "skip_done" gelmedigi testi).
    assert second.plan.verdict_map()[keys.compose_key("en:bank:noun", "de")] == "process"
    assert second.approved == 1


def test_deneme_gunlugune_ham_stable_key_gider(conns):
    cache, attempts = conns
    store, provider = MemoryStore(), FakeProvider()
    result = go(VariantJob(), store, provider,
               JobContext(tag="t", l2="en", variant="es"), conns)

    row = attempts.execute(
        "SELECT stable_key, variant FROM job_attempts WHERE run_id = ?",
        (result.run_id,)).fetchone()
    assert row["stable_key"] == "en:bank:noun"   # ham, bilesik degil
    assert row["variant"] == "es"
