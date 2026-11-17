"""
Imprime le bloc YAML `content: |-` d'un fichier réel du repo, prêt à coller dans un `filesChanged`
de stage_ui/public/demo_config.yaml, avec le nombre de lignes à reporter dans `added`.

Usage :
  uv run --frozen python .agents/skills/stage-ui-step-authoring/scripts/render_file_block.py <chemin> \
      [--indent 18] [--until "    columns:"]
"""

from __future__ import annotations

import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("path", help="Chemin du fichier, relatif à la racine du repo")
    parser.add_argument("--indent", type=int, default=18, help="Indentation du contenu (défaut : 18)")
    parser.add_argument("--until", default=None, help="Tronque avant la première ligne égale à cette valeur")
    args = parser.parse_args()

    file_path = (REPO_ROOT / args.path).resolve()
    lines = file_path.read_text(encoding="utf-8").rstrip("\n").split("\n")
    if args.until is not None and args.until in lines:
        lines = lines[: lines.index(args.until)]

    pad = " " * args.indent
    print(f"# path: {args.path}")
    print(f"# added: {len(lines)}")
    print(" " * (args.indent - 2) + "content: |-")
    for line in lines:
        print(pad + line if line.strip() else "")


if __name__ == "__main__":
    main()
