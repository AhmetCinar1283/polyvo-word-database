"""
Toplama — adim 1 (adaylar) ve adim 2 (kanit).

Ikisi de ingestor'lari gezer ama farkli seyler toplar: `collect_candidates`
evreni kurar, `collect_evidence` o evrenin UZERINE kanit ekler. Bu yuzden
`collect_evidence` her zaman `collect_candidates`'tan SONRA cagrilmalidir —
kanit, henuz var olmayan bir baslik icin evrene giremez.
"""

from __future__ import annotations

from typing import Iterable

from polyvo.dictionary import sources
from polyvo.dictionary.build import normalize, word_cleaner
from polyvo.dictionary.build.ingestors import Ingestor
from polyvo.dictionary.build.pool import Pool, Row


def collect_candidates(pool: Pool, ingestors: Iterable[Ingestor]) -> None:
    """Her ingestor'un `candidates()`'ini normalize edip `pool.rows`'a katar.

    Evren uretmeyen kaynaklar (`tier=None`, orn. `legacy_dist`) atlanir —
    K4: bu kaynaklar yalniz kanit verir.
    """
    for ing in ingestors:
        src = sources.get(ing.source_name)
        pool.counts.setdefault(src.name, {"candidates_in": 0, "evidence_in": 0})
        if src.tier is None:
            continue
        for cand in ing.candidates():
            head = normalize.normalize_headword(cand.headword)
            if head is None:
                pool.reject(str(cand.headword), cand.raw_pos, src.name, "bos_headword")
                continue
            bad = word_cleaner.reject_reason(head)
            if bad:
                pool.reject(head, cand.raw_pos, src.name, bad)
                continue
            pos = normalize.normalize_pos(cand.raw_pos)
            if cand.raw_pos and pos is None:
                # Kelime gecerli, ETIKET taninmiyor: satir POS'suz devam eder.
                pool.reject(head, cand.raw_pos, src.name, "pos_taninmiyor")
            key = (head, pos)
            row = pool.rows.get(key)
            if row is None:
                row = pool.rows[key] = Row(headword=head, pos=pos)
                if pos is not None:
                    row.pos_source = src.name
            row.absorb(tier=src.tier, cefr=cand.cefr,
                       freq_rank=cand.freq_rank, source=src.name)
            pool.counts[src.name]["candidates_in"] += 1


def collect_evidence(pool: Pool, ingestors: Iterable[Ingestor]) -> None:
    """Her ingestor'un `evidence()`'ini toplar; evren DISINDAKI baslikları atar.

    ipa-dict tek basina 125 bin satir tasir, buyuk cogunlugu ogretmedigimiz
    kelimelerdir — bu filtre olmadan `evidence` tablosu anlamsizca sisebilirdi.
    """
    universe = pool.universe()
    for ing in ingestors:
        src = sources.get(ing.source_name)
        for ev in ing.evidence():
            head = normalize.normalize_headword(ev.headword)
            if head is None:
                continue
            if head not in universe:
                pool.evidence_out_of_universe += 1
                continue
            payload = (ev.payload or "").strip()
            if not payload:
                continue
            pool.evidence.add((head, normalize.normalize_pos(ev.raw_pos),
                               ev.kind, payload, src.name))
            pool.counts[src.name]["evidence_in"] += 1
