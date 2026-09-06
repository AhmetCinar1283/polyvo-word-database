"""
MOTOR testleri: plan -> onay -> dongu -> yazma kapisi -> mutabakat.

Sahte bir saglayici (`FakeProvider`) ve sahte bir depo (`MemoryStore`)
kullanilir; hicbir ag cagrisi yoktur. Test edilen sey motorun DAVRANISIDIR:
`--dry-run` bir kurus harcamaz, ikinci kosu bedavadir (artimlilik), butce
tavani birimi yarim birakmaz, kapi engelledigi cevabi SEBEBIYLE raporlar.
"""

from __future__ import annotations

import os

import pytest

from polyvo.core.jobs import identity, schema
from polyvo.core.jobs.base import Job, JobContext, QaResult, Unit
from polyvo.core.jobs.engine import reconcile, run as engine_run
from polyvo.core.jobs.plan import planner, render
from polyvo.core.jobs.store.base import ArtifactStore, WriteRequest
from polyvo.core.jobs.store.policy import Existing, TIER_HUMAN, TIER_MODEL
from polyvo.core.llm.base import LLMResult
from polyvo.core.llm.cache import open_llm_cache_db


# ── Sahte parcalar ────────────────────────────────────────────────────────

class FakeProvider:
    """`complete_json` sozlesmesini taklit eden, agi olmayan saglayici."""

    def __init__(self, label="local:test", answers=None, fail_keys=()):
        self.label = label
        self.name = "fake"
        self.model = label.split(":", 1)[-1]
        self.calls: list[str] = []
        self.answers = answers or {}
        self.fail_keys = set(fail_keys)

    def preflight(self):
        """Sahte on-kontrol — her zaman gecer."""
        return None

    def complete_json(self, prompt, cache_conn, *, max_tokens, temperature,
                      pace_delay=0.0):
        """Onbellek-once davranisi dahil sahte bir cagri."""
        from polyvo.core.llm.cache import get_cached, hash_prompt, store_cached
        h = hash_prompt(self.label, prompt)
        hit = get_cached(cache_conn, h)
        if hit is not None:
            return LLMResult({"text": hit}, True, hit)
        self.calls.append(prompt)
        raw = self.answers.get(prompt, "tamam")
        store_cached(cache_conn, h, self.label, prompt, raw)
        return LLMResult({"text": raw}, False, raw)


class MemoryStore(ArtifactStore):
    """Bellekte tutan en kucuk gercek depo — kapiyi taban siniftan alir."""

    def __init__(self, rows=None):
        self.rows: dict[str, Existing] = dict(rows or {})
        self.payloads: dict[str, dict] = {}
        self.commits = 0

    def load_existing(self, ctx):
        """Mevcut satirlari doner."""
        return dict(self.rows)

    def _write_row(self, ctx, request: WriteRequest):
        """Kapiyi gecmis satiri belleğe yazar."""
        self.rows[request.unit.key] = Existing(tier=request.tier,
                                               status=request.status,
                                               rank=request.rank)
        self.payloads[request.unit.key] = request.payload

    def commit(self):
        """Commit sayacini artirir."""
        self.commits += 1


class WordJob(Job):
    """Uc kelimeyi isleyen en kucuk gercek is."""

    family, kind, command, prompt_version = "test", "card", "test-card", "v1"

    def __init__(self, words=("bank", "book", "cup"), reject=()):
        self.words = list(words)
        self.reject = set(reject)

    def load_units(self, ctx):
        """Kelime basina bir birim."""
        return [Unit(key=f"en:{w}", name=w, data={"w": w}) for w in self.words]

    def build_prompt(self, unit, retry_note=None):
        """Deterministik prompt; `retry_note` metni degistirir."""
        return f"kelime: {unit.data['w']}" + (f" | not: {retry_note}" if retry_note else "")

    def run_qa(self, parsed, unit):
        """Adi `reject` kumesinde olan birimler reddedilir."""
        if unit.name in self.reject:
            return QaResult(False, "test_reddi", {"w": unit.name})
        return QaResult(True, None, {"w": unit.name, "cevap": (parsed or {}).get("text")})


@pytest.fixture
def conns(tmp_path):
    """Gecici LLM onbellegi + deneme gunlugu baglantilari."""
    cache = open_llm_cache_db(str(tmp_path / "llm_cache.sqlite"))
    attempts = schema.open_attempts(str(tmp_path / "attempts.sqlite"))
    yield cache, attempts
    cache.close()
    attempts.close()


def go(job, store, provider, conns, **kw):
    """Motoru sahte parcalarla kostur — testlerdeki tekrari azaltir."""
    cache, attempts = conns
    return engine_run.run(job, JobContext(tag="t", l2="en"), provider=provider,
                          store=store, cache_conn=cache, attempts_conn=attempts,
                          assume_yes=True, **kw)


# ── Kimlik tahsisi ────────────────────────────────────────────────────────

def test_kimlik_monotonik_ve_geri_gitmez(tmp_path):
    path = str(tmp_path / "identity.sqlite")
    conn = schema.open_identity(path)
    assert list(identity.allocate(conn, "item_id", 3)) == [1, 2, 3]
    assert identity.allocate_one(conn, "item_id") == 4
    conn.commit()
    conn.close()

    # Depo yeniden acildiginda sayac KALDIGI yerden devam eder.
    conn = schema.open_identity(path)
    assert identity.current(conn, "item_id") == 5
    # `floor` yalnizca ILK kurulusta okunur: var olan sayaci geri alamaz.
    assert identity.allocate_one(conn, "item_id", floor=100) == 5
    conn.close()


def test_kimlik_floor_ile_baslar(tmp_path):
    """Elle kopyalanmis bir depo: tahsis MAX(id)'nin ustunden devam eder."""
    conn = schema.open_identity(str(tmp_path / "i.sqlite"))
    assert identity.allocate_one(conn, "sense_id", floor=4200) == 4201
    conn.close()


# ── Plan ve --dry-run ─────────────────────────────────────────────────────

def test_dry_run_tek_kurus_harcamaz(conns):
    provider = FakeProvider()
    result = go(WordJob(), MemoryStore(), provider, conns, dry_run=True)
    assert provider.calls == []           # HIC dis cagri yok
    assert result.new_calls == 0
    assert result.plan.paid_calls == 3    # plan yine de maliyeti soyler


def test_plan_bicimi_odenecek_cagriyi_yazar(conns):
    cache, _ = conns
    plan = planner.make_plan(WordJob(), WordJob().load_units(None), {},
                             model_label="local:test", model_rank=50,
                             mode="none", cache_conn=cache)
    lines = render.format_plan(plan)
    assert any("PLAN" in ln for ln in lines)
    assert any("ODENECEK DIS CAGRI : 3" in ln for ln in lines)
    assert any("satir yok — ilk uretim" in ln for ln in lines)


def test_plan_insan_satirini_atlar_ve_sebebini_yazar(conns):
    cache, _ = conns
    job = WordJob()
    existing = {"en:bank": Existing(tier=TIER_HUMAN)}
    plan = planner.make_plan(job, job.load_units(None), existing,
                             model_label="local:test", model_rank=50,
                             mode="none", cache_conn=cache)
    assert plan.paid_calls == 2
    assert plan.skipped() == {"skip_human": 1}
    assert any("insan karari" in ln for ln in render.format_plan(plan))


# ── Artimlilik ────────────────────────────────────────────────────────────

def test_ikinci_kosu_bedavadir(conns):
    """§2'nin artimlilik kurali: odenmis bir karar bir daha odenmez."""
    store, provider = MemoryStore(), FakeProvider()
    first = go(WordJob(), store, provider, conns)
    assert first.approved == 3 and first.new_calls == 3

    second = go(WordJob(), store, provider, conns)
    assert second.plan.paid_calls == 0
    assert second.new_calls == 0
    assert second.skipped == 3


def test_onbellek_dolu_ama_depo_bossa_cagri_odenmez(conns):
    """Depo silinse bile LLM onbellegi sicak kalir — plan bunu GORUR."""
    provider = FakeProvider()
    go(WordJob(), MemoryStore(), provider, conns)
    result = go(WordJob(), MemoryStore(), provider, conns)   # depo sifirlandi
    assert result.plan.process_total == 3
    assert result.plan.cached_calls == 3
    assert result.plan.paid_calls == 0
    assert result.new_calls == 0


# ── Yazma kapisi ve butce ─────────────────────────────────────────────────

def test_kapi_insan_satirini_korur_ve_sebebini_raporlar(conns):
    """Odenmis ama YAZILMAMIS cevap sessizce kaybolmaz."""
    store = MemoryStore({"en:bank": Existing(tier=TIER_HUMAN)})
    result = go(WordJob(), store, FakeProvider(), conns, redo="bad")
    # `bad` modunda bile insan satirina cagri gitmez.
    assert result.plan.skipped().get("skip_human") == 1
    assert store.rows["en:bank"].tier == TIER_HUMAN


def test_kapi_engellediginde_sebep_ozete_girer(conns):
    """Zayif model, onayli bir satiri ezemez ve bu ozete SEBEBIYLE yazilir."""
    # Modeli BILINMEYEN, reddedilmis bir satir: verdikt "dene" der (bilmiyorum
    # bir yukseltmeyi engellememeli), ama deneme de reddedilirse kapi mevcut
    # satiri korur — cunku iki modelin hangisinin iyi oldugu bilinmiyor.
    store = MemoryStore({"en:bank": Existing(tier=TIER_MODEL, status="rejected",
                                             rank=None)})
    job = WordJob(words=["bank"], reject=["bank"])
    result = go(job, store, FakeProvider(label="gemini:test"), conns)
    assert result.rejected == 1
    assert result.blocked == 1
    assert result.block_reasons == {"model_karsilastirilamadi": 1}
    assert any("model_karsilastirilamadi" in ln
               for ln in reconcile.reconcile(result))


def test_butce_tavani_kalan_birimlere_dokunmaz(conns):
    provider = FakeProvider()
    result = go(WordJob(), MemoryStore(), provider, conns, max_new=2)
    assert result.budget_stopped
    assert len(provider.calls) == 2
    assert result.processed == 2


def test_butce_dolunca_mutabakat_uyari_basmaz(conns):
    """Butceyle duran kosu plandan az cagri yapar — bu bir sapma DEGILDIR."""
    result = go(WordJob(), MemoryStore(), FakeProvider(), conns, max_new=2)
    lines = reconcile.reconcile(result)
    assert not any("UYARI" in ln for ln in lines)
    assert any("butcesi doldu" in ln for ln in lines)


def test_mutabakat_gercek_sapmayi_yakalar(conns):
    result = go(WordJob(), MemoryStore(), FakeProvider(), conns)
    result.new_calls += 7          # motorun disinda uydurulmus bir sapma
    assert any("UYARI" in ln for ln in reconcile.reconcile(result))


# ── Deneme gunlugu ────────────────────────────────────────────────────────

def test_reddedilen_deneme_gunluge_yazilir(conns):
    cache, attempts = conns
    job = WordJob(words=["bank", "book"], reject=["bank"])
    result = go(job, MemoryStore(), FakeProvider(), conns)
    rows = attempts.execute(
        "SELECT status, reject_reason FROM job_attempts WHERE run_id = ?",
        (result.run_id,)).fetchall()
    durumlar = sorted(r["status"] for r in rows)
    assert durumlar == ["approved", "rejected"]
    assert any(r["reject_reason"] == "test_reddi" for r in rows)


def test_deneme_gunlugu_red_dokumu_verir(conns):
    from polyvo.core.jobs import attempts as attempt_log
    cache, conn = conns
    job = WordJob(words=["bank", "book"], reject=["bank", "book"])
    result = go(job, MemoryStore(), FakeProvider(), conns)
    assert attempt_log.reject_reasons(conn, result.run_id) == {"test_reddi": 2}


def test_yeniden_deneme_farkli_prompt_uretir(conns):
    """`retry_note` prompt'u degistirir — aksi halde ayni onbellek satiri."""
    provider = FakeProvider()

    class IkiDenemeli(WordJob):
        max_attempts = 2

    job = IkiDenemeli(words=["bank"], reject=["bank"])
    result = go(job, MemoryStore(), provider, conns)
    assert len(provider.calls) == 2
    assert provider.calls[0] != provider.calls[1]
    # Cok denemeli iste plan bir ARALIKTIR; 2 cagri o araligin icinde.
    assert result.plan.paid_calls <= result.new_calls <= result.plan.paid_calls_max
    assert not any("UYARI" in ln for ln in reconcile.reconcile(result))


# ── Depo sozlesmesi ───────────────────────────────────────────────────────

def test_yazma_kapisi_atlanamaz():
    """`_write_row` public degildir; disaridan tek yol `save`tir."""
    assert not hasattr(ArtifactStore, "write_row")
    assert "_write_row" in ArtifactStore.__abstractmethods__
    assert "load_existing" in ArtifactStore.__abstractmethods__


def test_stores_dosyalari_data_stores_altinda():
    """Kimlik ve deneme gunlugu 'serbestce silinebilir' bir dizinde duramaz."""
    for path in (schema.identity_path(), schema.attempts_path()):
        assert os.path.normpath(path).replace("\\", "/").endswith(
            f"data/stores/{os.path.basename(path)}")
