"""
SAHNE/ALAN KISITI — cesitliligin OLCULEBILIR araci.

Cesitlilik prompt'a "cesitli ol" yazarak saglanmaz: olculmeyen istek tutulmaz
(gecmis sikayet: "I eat cake" tekduzeligi). Bunun yerine her soruya sabit bir
listeden bir sahne ONERILIR.

ONERI, KISIT DEGIL (2026-09-07). Once zorunluydu; sahne yalnizca
`stable_key`ten turedigi icin kelimeyle ilgisiz duser ve zorunlu oldugunda
model hedef kelimeyi ilgisiz bir sahneye sikistirir ya da dusurur — olculdu,
gerekcesi ve sayilari `prompt.py` docstring'indedir. Bu dosyanin isi
DEGISMEDI (deterministik, birbirinden farkli uc sahne uretmek); degisen,
prompt'un bu uretimi ne kadar baglayici sundugudur.

Bunun bir BEDELI var ve acikca kabul edilir: "ucu de ayni sahne hissi
veriyor" hali artik yalnizca oneriyle engellenir, garanti edilmez. Zaten
olculebilen tek cesitlilik acilis n-gram'idir (`qa/variety.py`) ve o kapi
REDDETMEYE devam eder; sahne hissi hicbir zaman olculemiyordu.

Kisit DETERMINISTIKTIR: yalnizca `stable_key` ve soru sirasindan turer.
Saatten, rastgeleden ya da kosu kimliginden TUREMEZ — ayni birim yeniden
kosuldugunda ayni kisit gelmeli, yoksa "bir kere odenir" kurali kirilir
(onbellek de tutmaz).

Bir anlamin uc sorusu BIRBIRINDEN FARKLI sahne alir: ayni sahne uc kez
verilirse tekduzelik kapisi (`qa/variety.py`) is bulur.
"""

from __future__ import annotations

from hashlib import blake2s

from polyvo.modules.cloze.difficulty import QUESTION_COUNT

#: Sahne listesi SABITTIR ve siralidir — degistirmek uretilen kisitlari
#: degistirir, yani prompt'u degistirir (`prompt_version` artirilmali).
SCENES: tuple[str, ...] = (
    "at home, everyday family life",
    "at work or in an office",
    "travelling: airport, train, hotel",
    "at school or while studying",
    "health: doctor, illness, exercise",
    "shopping and paying for things",
    "food, cooking and eating out",
    "sport and free time",
    "nature, weather and outdoors",
    "technology, phones and computers",
    "money, banking and bills",
    "friends, neighbours and social life",
    "city life: streets, transport, rules",
    "news, work meetings and plans",
)


def _index(stable_key: str, seq: int, size: int) -> int:
    """`(stable_key, seq)` icin sabit bir liste indeksi (kriptografik degil,
    yalnizca dagitim icin)."""
    digest = blake2s(f"{stable_key}#{seq}".encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") % size


def scenes_for(stable_key: str) -> tuple[str, ...]:
    """Bir anlamin uc sorusu icin UC FARKLI sahne, deterministik sirada."""
    pool = list(SCENES)
    chosen: list[str] = []
    for seq in range(1, QUESTION_COUNT + 1):
        chosen.append(pool.pop(_index(stable_key, seq, len(pool))))
    return tuple(chosen)


def scene_for(stable_key: str, seq: int) -> str:
    """Tek bir sorunun sahne kisiti (`seq` 1'den baslar)."""
    return scenes_for(stable_key)[seq - 1]
