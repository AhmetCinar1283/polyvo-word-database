"""
Varyanta duyarli depo anahtari — TEK uretim yeri.

`variant` motor tarafinda bir ANAHTAR bilesenidir; depoda bir sutun olmak
ZORUNDA DEGILDIR (ornegin `sense_gloss_l1`in dogal anahtari zaten
`(sense_id, l1)`, ayrica bir `variant` sutunu tekrar etmez). Bu dosyanin
disinda hicbir modul kendi ayiricisini uydurmamali.

Bos varyant = bugunku davranis: `compose_key(x, "")` HER ZAMAN `x`in
kendisidir (bit bit ayni dizgi) — geriye donuk uyum boyle korunur, mevcut
satirlar icin migration gerekmez.
"""

from __future__ import annotations

from polyvo.core.jobs.base import Unit

#: Ham stable_key ile varyant arasindaki ayirici. `stable_key` zaten `:`
#: kullandigi icin (`en:bank:noun`) okunurlukte karismasin diye `::` secildi.
_SEPARATOR = "::"


def compose_key(stable_key: str, variant: str) -> str:
    """`(stable_key, variant)` cifti icin motor anahtarini uretir.

    `variant` bos ise sonuc ham `stable_key` ile birebir aynidir."""
    if not variant:
        return stable_key
    return f"{stable_key}{_SEPARATOR}{variant}"


def with_variant(unit: Unit, variant: str) -> Unit:
    """Bir `Unit`i varyanta duyarli anahtara tasir.

    Ham `stable_key`, gunluk/rapor icin `unit.data['stable_key']`de saklanir.
    `variant` bos ise `unit` DEGISTIRILMEDEN doner (ayni obje)."""
    if not variant:
        return unit
    return Unit(
        key=compose_key(unit.key, variant),
        name=f"{unit.name} [{variant}]",
        data={**unit.data, "stable_key": unit.key},
    )
