"""
POS cozumu — K7 karari burada uygulanir.

NGSL/TSL/BSL/New Dolch POS tasimaz; ayni baslik icin POS'suz bir satir ile
POS'lu satir(lar) birlikte yasayabilir. Bu fonksiyon ikisini TEK satira
indirger:

  1. Ayni basligin POS'lu satiri VARSA, POS'suz satir onun tier/CEFR/kaynak
     bilgisini birakip kaybolur (kendi basina bir aday degildir).
  2. YOKSA, `evidence`'taki `kind="pos"` kayitlarina (orn. `legacy_dist`)
     bakilir; bulunursa POS oradan alinir.
  3. O da yoksa satir POS'SUZ KALIR — atilmaz, `pool.unresolved`'a
     `pos_kaynagi_yok` sebebiyle raporlanir.
"""

from __future__ import annotations

from collections import defaultdict

from polyvo.dictionary.build import normalize
from polyvo.dictionary.build.pool import Pool


def resolve_pos(pool: Pool) -> tuple[int, int]:
    """`(kanittan_cozulen, pos_suz_kalan)` sayilarini doner; `pool.rows`'u yerinde gunceller."""
    by_head: dict[str, list] = defaultdict(list)
    for row in pool.rows.values():
        by_head[row.headword].append(row)

    pos_evidence: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for head, _pos, kind, payload, source in pool.evidence:
        if kind == "pos":
            canon = normalize.normalize_pos(payload)
            if canon:
                pos_evidence[head].append((canon, source))

    recovered = missing = 0
    for head, group in by_head.items():
        blank = next((r for r in group if r.pos is None), None)
        if blank is None:
            continue
        typed = [r for r in group if r.pos is not None]
        if typed:
            for row in typed:
                row.absorb(tier=blank.tier, cefr=blank.cefr,
                           freq_rank=blank.freq_rank, source=None)
                row.srcs |= blank.srcs
            del pool.rows[(head, None)]
            continue
        found = pos_evidence.get(head)
        if found:
            canon, source = sorted(found)[0]
            del pool.rows[(head, None)]
            blank.pos, blank.pos_source = canon, source
            pool.rows[(head, canon)] = blank
            recovered += 1
        else:
            pool.reject(head, None, ",".join(sorted(blank.srcs)), "pos_kaynagi_yok")
            missing += 1
    return recovered, missing
