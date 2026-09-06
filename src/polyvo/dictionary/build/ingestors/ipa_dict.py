"""
ipa-dict en_US — telaffuz (MIT, SEVK EDILEBILIR).

IPA bir OLGUDUR, ifade degil; bu yuzden `sources.ipa_dict.shippable=True`
(bkz. docs/SOURCES.md §4). Yalniz `en_US` alinir: `en_UK` dosyasi GPL 3.0
tureviydi ve depoya sokulmasi tum hattı GPL'e baglardi.

Bicim: `word<TAB>/ˈwɜrd/, /wɝd/` — bir satirda birden cok varyant olabilir,
ilki birincil kabul edilir.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from polyvo.dictionary.build.ingestors.base import Evidence, FileIngestor


@dataclass
class IpaDictIngestor(FileIngestor):
    """ipa-dict en_US dosyasini okur; aday uretmez, yalniz IPA kaniti verir."""
    source_name: str = "ipa_dict"

    def evidence(self) -> Iterable[Evidence]:
        """Her satirdaki telaffuz varyantlarindan birer `ipa` kaniti uretir."""
        if not self.available():
            return
        with open(self.raw_path(), encoding="utf-8") as fh:
            for line in fh:
                word, _, rest = line.partition("\t")
                word = word.strip()
                if not word or not rest.strip():
                    continue
                for variant in rest.split(","):
                    variant = variant.strip()
                    if variant:
                        yield Evidence(word, kind="ipa", payload=variant)


INGESTOR = IpaDictIngestor()
