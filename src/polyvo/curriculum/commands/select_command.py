"""
`polyvo curriculum select` — evreni secer, kimlik tahsis eder, workspace'e
izdusurur.

Bu dosya IS YAPMAZ: sirayla `universe.read_candidates` -> `universe.select_universe`
-> `universe.gate` -> `items.assign_identities` -> `items.write_workspace` cagirir
ve `source_config.json` kilidini yazar. Mantigin kendisi cagirdigi dosyalardadir
(`dictionary/build/commands/build_command.py` ile ayni desen).
"""

from __future__ import annotations

import argparse

from polyvo.core import config, paths
from polyvo.curriculum import items, schema, universe
from polyvo.dictionary.build import stages as dict_stages


def add_select_args(parser: argparse.ArgumentParser) -> None:
    """`--tag`, `--l2` ve evren hedefini gecici degistiren `--target-size`."""
    parser.add_argument("--tag", "--data-title", dest="tag", default=None,
                        help="Veri basligi (yoksa polyvo.toml/ortam/tek aday)")
    parser.add_argument("--l2", default=None,
                        help="Hedef dil (varsayilan: polyvo.toml project.l2)")
    parser.add_argument("--target-size", type=int, default=None,
                        help="Evren buyuklugu (varsayilan: polyvo.toml universe.target_size)")


def cmd_select(args: argparse.Namespace) -> int:
    """Evreni secer, kimlik tahsis eder, `workspace/<tag>/<l2>/universe.sqlite`'a yazar."""
    tag = paths.resolve_tag(args.tag)
    l2 = args.l2 or config.default_l2()
    target_size = args.target_size or config.universe_target_size()

    db_path = dict_stages.lexicon_db_path(tag)
    try:
        candidates, pos_missing = universe.read_candidates(db_path)
        selection = universe.select_universe(
            candidates, target_size=target_size, pos_missing_count=pos_missing)
        universe.gate(selection)
    except universe.UniverseError as exc:
        print(f"[polyvo] evren kapisi ihlal edildi, HICBIR DOSYA YAZILMADI:\n  {exc}")
        return 1

    conn = schema.open_identity_db()
    try:
        projected = items.assign_identities(conn, l2, selection.kept)
    finally:
        conn.close()

    ws_path = items.write_workspace(tag, l2, projected)
    lock_path = schema.write_source_config(tag, l2, {
        "source_lexicon": db_path,
        "source_row_counts": dict_stages.lexicon_row_counts(tag),
        "target_size": target_size,
        "universe_size": selection.size,
        "excluded_pos_missing": selection.excluded_pos_missing,
        "excluded_over_target": selection.excluded_over_target,
    })

    print(f"tag {tag}  l2 {l2}  evren {selection.size} kelime "
          f"(hedef {target_size}, pos-suz elenen {selection.excluded_pos_missing}, "
          f"hedef-disi elenen {selection.excluded_over_target})")
    print(f"\n  {ws_path}\n  {lock_path}")
    return 0
