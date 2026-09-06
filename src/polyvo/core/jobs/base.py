"""
Bir isin uymasi gereken SOZLESME — motorun modulden bekledigi tek sey.

Burada hicbir davranis yok, yalnizca tanim: bir birim nedir (`Unit`), bir
kosunun degismeyen girdileri nedir (`JobContext`), bir QA sonucu nedir
(`QaResult`) ve bir is neyi uygulamak zorundadir (`Job`).

Sozlesmeyi bilerek UC metoda indirdik. Eski repoda modul taban sinifi
buyudukce her yeni is ondan tasidigi ama kullanmadigi alanlar aliyordu;
sonucta "yeni bir is yazmak" bir taban sinifi okumayi gerektiriyordu.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Unit:
    """Tek bir LLM cagrisinin birimi.

    `key` depo anahtaridir (kalici, `stable_key`); `name` yalnizca raporda
    gorunen okunakli addir; `data` ise `build_prompt`in ihtiyac duydugu ham
    girdidir. Ikisini ayirmak sart: rapor metnini degistirmek depo
    anahtarini ASLA degistirmemeli."""

    key: str
    name: str
    data: dict = field(default_factory=dict)


@dataclass
class JobContext:
    """Bir kosunun degismeyen girdileri (tag, diller, varyant, sinir)."""

    tag: str
    l2: str = "en"
    l1: str = ""
    variant: str = ""
    limit: int | None = None


@dataclass
class QaResult:
    """`run_qa` ciktisi: gecti mi, sebep, depoya yazilacak yuk.

    `reason` ONAYDA DA dolu olabilir: garanti edilemeyen bir QA kontrolu
    reddetmez, uyarir (§6.7). O uyari metni kaybolmamali."""

    ok: bool
    reason: str | None = None
    payload: dict = field(default_factory=dict)


class Job(ABC):
    """Bir LLM uretim isi. Alt sinif yalnizca uc metodu uygular."""

    #: Depo satir ailesi — bir app'in tum `kind`'lari ayni `family`'yi paylasir.
    family: str = ""
    #: Ailenin icindeki alt tur (`card`, `gloss_tr`, `example`, ...).
    kind: str = ""
    #: Rapor ve gunluk etiketi (`polyvo <app> <komut>` ile ayni ad).
    command: str = ""
    #: Prompt degistiginde ELLE artirilir; deneme gunlugune yazilir.
    prompt_version: str = "v1"

    max_attempts: int = 1
    max_tokens: int = 1200
    temperature: float = 0.4

    def prepare(self, ctx: JobContext) -> None:
        """Kosu oncesi tek seferlik hazirlik. Varsayilan: hicbir sey."""
        return None

    @abstractmethod
    def load_units(self, ctx: JobContext) -> list[Unit]:
        """Bu kosuda islenecek birimleri — SIRALI ve tekrarsiz — dondurur."""

    @abstractmethod
    def build_prompt(self, unit: Unit, retry_note: str | None = None) -> str:
        """Birimin prompt metni. `retry_note` bir onceki red sebebidir."""

    @abstractmethod
    def run_qa(self, parsed: dict | None, unit: Unit) -> QaResult:
        """Modelin cevabini dogrular ve depoya yazilacak yuku uretir."""
