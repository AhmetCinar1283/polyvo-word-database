"""
YAZMA KAPISI ve REDO MATRISI testleri — Adim 2'nin kabul kosulu.

Ikisi de saf fonksiyon oldugu icin burada veritabani yok: matrisin tamami
tek tek, acikca yazilir. Bir kuralin degistirilmesi bu dosyada gorunur bir
satirin degismesini gerektirsin diye matris `parametrize` ile DUZ yazildi,
donguyle uretilmedi.
"""

from __future__ import annotations

import pytest

from polyvo.core.jobs.plan import verdict as vd
from polyvo.core.jobs.store import policy


def ex(tier=policy.TIER_MODEL, status="approved", rank=50) -> policy.Existing:
    """Kisa yoldan bir `Existing` uretir."""
    return policy.Existing(tier=tier, status=status, rank=rank)


# ── Yazma kapisi ──────────────────────────────────────────────────────────

def test_bos_satira_yazilir():
    assert policy.should_write(None, new_tier=3, new_status="approved",
                               new_rank=50).write


def test_insan_karari_her_seyi_ezer():
    d = policy.should_write(ex(tier=policy.TIER_HUMAN), new_tier=policy.TIER_HUMAN,
                            new_status="approved", new_rank=None)
    assert d.write and d.reason == "insan_karari"


def test_makine_insan_kararini_ezemez():
    d = policy.should_write(ex(tier=policy.TIER_HUMAN), new_tier=policy.TIER_MODEL,
                            new_status="approved", new_rank=1)
    assert not d.write and d.reason == "mevcut_insan_karari"


def test_daha_guvenilir_tier_korunur():
    d = policy.should_write(ex(tier=policy.TIER_DICT_SEED), new_tier=policy.TIER_MODEL,
                            new_status="approved", new_rank=1)
    assert not d.write and d.reason == "mevcut_daha_guvenilir_tier"


def test_onayli_satir_reddedilenle_ezilmez():
    """Eski repoda olculen kusur: bitmis is sessizce gorus alanindan cikiyordu."""
    d = policy.should_write(ex(status="approved"), new_tier=3,
                            new_status="rejected", new_rank=1)
    assert not d.write and d.reason == "onayliyi_reddedilenle_ezme"


def test_reddedilmis_satirin_uzerine_onayli_yazilir():
    d = policy.should_write(ex(status="rejected"), new_tier=3,
                            new_status="approved", new_rank=99)
    assert d.write and d.reason == "bosluk_dolduruldu"


def test_daha_iyi_model_yazar_esit_model_yazmaz():
    assert policy.should_write(ex(rank=50), new_tier=3, new_status="approved",
                               new_rank=10).write
    d = policy.should_write(ex(rank=50), new_tier=3, new_status="approved",
                            new_rank=50)
    assert not d.write and d.reason == "esit_ya_da_zayif_model"


def test_karsilastirilamayan_model_yazmaz():
    """Bilinmeyen rank bir YUKSELTME gerekcesi degildir."""
    assert not policy.should_write(ex(rank=None), new_tier=3,
                                   new_status="approved", new_rank=10).write


# ── Redo matrisi ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("mode,beklenen", [
    ("none", "process"),
    ("bad", "process"),
    ("only-bad", "skip_missing"),
])
def test_matris_satir_yok(mode, beklenen):
    assert vd.decide(None, mode=mode, model_rank=10) == beklenen


@pytest.mark.parametrize("mode", vd.REDO_MODES)
def test_matris_insan_her_modda_dokunulmaz(mode):
    assert vd.decide(ex(tier=policy.TIER_HUMAN), mode=mode,
                     model_rank=1) == "skip_human"


@pytest.mark.parametrize("mode,beklenen", [
    ("none", "skip_done"),
    ("bad", "skip_not_bad"),
    ("only-bad", "skip_not_bad"),
])
def test_matris_onayli_satira_cagri_yok(mode, beklenen):
    assert vd.decide(ex(status="approved"), mode=mode, model_rank=1) == beklenen


@pytest.mark.parametrize("mode", vd.REDO_MODES)
def test_matris_kotu_satir_esit_modelde_atlanir(mode):
    """Ayni model + ayni prompt = onbellekten ayni cevap. Yeni bilgi yok."""
    assert vd.decide(ex(status="rejected", rank=50), mode=mode,
                     model_rank=50) == "skip_outranked"


@pytest.mark.parametrize("mode", vd.REDO_MODES)
def test_matris_kotu_satir_daha_iyi_modelde_islenir(mode):
    assert vd.decide(ex(status="rejected", rank=50), mode=mode,
                     model_rank=10) == "process"


@pytest.mark.parametrize("mode", vd.REDO_MODES)
def test_matris_modeli_bilinmeyen_kotu_satir_islenir(mode):
    """'Bilmiyorum' bir yukseltmeyi engellememeli."""
    assert vd.decide(ex(status="rejected", rank=None), mode=mode,
                     model_rank=90) == "process"


def test_bilinmeyen_mod_hata_verir():
    with pytest.raises(ValueError):
        vd.decide(None, mode="hepsini-sil", model_rank=10)


def test_process_sebebi_raporlanabilir():
    assert vd.process_reason(None) == "eksik"
    assert vd.process_reason(ex(status="rejected")) == "reddedilmis_onarim"
    for reason in ("eksik", "reddedilmis_onarim"):
        assert reason in vd.PROCESS_REASON_LABELS


def test_her_skip_verdiktinin_bir_etiketi_var():
    """Etiketsiz bir verdikt, raporda ham kod adi olarak gorunurdu."""
    uretilenler = set()
    for mode in vd.REDO_MODES:
        for row in (None, ex(tier=policy.TIER_HUMAN), ex(status="approved"),
                    ex(status="rejected", rank=50)):
            uretilenler.add(vd.decide(row, mode=mode, model_rank=50))
    uretilenler.discard(vd.PROCESS)
    assert uretilenler <= set(vd.SKIP_REASON_LABELS)
