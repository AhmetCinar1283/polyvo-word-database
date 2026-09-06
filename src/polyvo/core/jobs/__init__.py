"""
Katman 0 — genel uretim motoru: HER LLM isi ayni kosuyu kullanir.

Bir "is" (`Job`) yalnizca uc soruyu cevaplar: neyi isleyecegim
(`load_units`), prompt ne (`build_prompt`), gelen cevap gecerli mi
(`run_qa`). Geri kalan her sey burada, tek yerde ve her is icin AYNIDIR:
plan raporu, onbellek yoklamasi, onay istemi, butce, deneme gunlugu,
tier korumali yazma ve kosu sonu mutabakati.

Gerekce (§2): "bunu daha once yazdim mi" kontrolu MOTORUN ICINDE tek bir
kapidir. Eski repoda bu kontrol her modulde yeniden yazilmisti ve
kopyalar birbirinden sessizce ayrisiyordu.
"""
