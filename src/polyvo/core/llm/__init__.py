"""LLM saglayici katmani. Bu paket import edildigi an tum saglayicilar
`registry.py`ye kayit olur (bkz. `providers/__init__.py`) — `--provider`
secenekleri, interaktif menu ve `registry.create()` hep dolu bir kayit
defterine bakar, cagiranin ayrica bir "kayit modulu" import etmesi gerekmez."""

from polyvo.core.llm import providers as _providers  # noqa: F401
