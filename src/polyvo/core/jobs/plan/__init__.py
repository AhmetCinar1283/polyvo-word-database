"""
Kosu-oncesi plan: TEK LLM cagrisi yapmadan "ne olacak, kac para" cevabi.

`verdict.py` karari (saf), `planner.py` bu karari her birime uygulayip
onbellegi yoklar, `report.py` sayaclari tutar, `render.py` ekrana basar,
`confirm.py` onay ister. Plan ile gercek kosunun ayrisamamasinin sebebi
ikisinin de AYNI `verdict.decide` ve AYNI `build_prompt` + `hash_prompt`
ciftini kullanmasidir.
"""
