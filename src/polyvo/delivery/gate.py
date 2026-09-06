"""
SEVK KAPISI. Tek isi var: bu satirlar ogrenciye gidebilir mi?

Kural (§6.1): uyari basip devam eden kapi, kapi DEGILDIR. Ihlal varsa
`materialize` SIFIR dosya yazar ve exit 1 doner. Bu yuzden kapi butun
satirlari once toplu olarak degerlendirir, tek tek yazarken degil.

Kapinin dayandigi ayrim `dictionary/sources.py`'de yazilidir: OLGU (frekans,
CEFR, IPA) her zaman sevk edilebilir; IFADE (tanim, ornek cumle, aciklama)
yalnizca `shippable=True` bir kaynaktan ya da bizim urettigimizden gelebilir.
"""

from __future__ import annotations

from dataclasses import dataclass

from polyvo.delivery.collect import SHIPPABLE_STATUS, Shipment
from polyvo.dictionary import sources

#: Kendi urettigimiz metnin kaynak adlari (`modules/lexicon_card/store.py`).
OWN_TEXT_SOURCES = frozenset({"llm", "human"})

#: Ihlal listesinde en fazla kac ornek gosterilir (rapor okunabilir kalsin).
MAX_SAMPLES = 5


class ShipGateError(RuntimeError):
    """Kapi ihlali. Yakalayan taraf SIFIR dosya yazmakla yukumludur."""


@dataclass
class Violation:
    """Tek bir kapi ihlali: kural adi + kac satir + ornekler."""
    rule: str
    count: int
    samples: list[str]

    def __str__(self) -> str:
        """Rapor satiri."""
        return f"{self.rule}: {self.count} satir  ->  " + ", ".join(self.samples)


def allowed_text_sources() -> frozenset[str]:
    """Metni sevk edilebilen kaynak adlari: bizimkiler + `shippable=True`."""
    return OWN_TEXT_SOURCES | {s.name for s in sources.SOURCES.values() if s.shippable}


def check(shipment: Shipment) -> list[Violation]:
    """Sevkiyati dogrular; ihlal listesi doner (bos liste = temiz)."""
    allowed = allowed_text_sources()
    buckets: dict[str, list[str]] = {}

    def flag(rule: str, label: str) -> None:
        """Bir ihlali kuralina gore biriktirir (tek raporda basilsin diye)."""
        buckets.setdefault(rule, []).append(label)

    seen_items: set[int] = set()
    seen_senses: set[int] = set()
    for row in shipment.rows:
        label = f"{row.stable_key} (item {row.item_id})"

        leaked = sorted(row.text_sources - allowed)
        if leaked:
            flag("sevk_edilemez_kaynaktan_metin", f"{label} <- {','.join(leaked)}")
        if row.status != SHIPPABLE_STATUS:
            flag("onaylanmamis_satir", f"{label} [{row.status}]")
        if not (row.gloss_en or "").strip():
            flag("gloss_en_bos", label)
        if not (row.headword or "").strip():
            flag("headword_bos", label)
        if shipment.l1 and not (row.gloss_l1 or "").strip():
            flag("l1_karsiligi_yok", label)
        if any(not ex.strip() for ex in row.examples):
            flag("bos_ornek_cumle", label)

        # Kimlik tekilligi: iki satir ayni id'yi paylasirsa Flutter tarafinda
        # sessizce biri kaybolur — sevkiyattan ONCE yakalanmali.
        if row.item_id in seen_items:
            flag("item_id_tekrar_ediyor", label)
        if row.sense_id in seen_senses:
            flag("sense_id_tekrar_ediyor", label)
        seen_items.add(row.item_id)
        seen_senses.add(row.sense_id)

    if not shipment.rows:
        flag("sevk_edilecek_satir_yok", f"tag {shipment.tag}, l2 {shipment.l2}")

    return [Violation(rule=rule, count=len(labels), samples=labels[:MAX_SAMPLES])
            for rule, labels in sorted(buckets.items())]


def enforce(shipment: Shipment) -> None:
    """Ihlal varsa `ShipGateError` firlatir — cagiran HICBIR dosya yazmamis olmali."""
    violations = check(shipment)
    if violations:
        raise ShipGateError("\n  ".join(str(v) for v in violations))
