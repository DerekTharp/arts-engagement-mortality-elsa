"""
Build the JECH submission .docx files from the rendered manuscript markdown.

manuscript.docx needs a title page injected because pandoc's docx writer drops
the YAML author block; the supplement, STROBE checklist, and cover letter
convert directly. All are run through postformat_docx.py (table formatting,
single spacing, Times New Roman). The manuscript title-page word counts are
computed from manuscript.md so they track edits automatically.

Usage: python3 code/build_submission_docx.py
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_shared_ref = Path.home() / "research-templates" / "templates" / "reference.docx"
REF = _shared_ref if _shared_ref.exists() else ROOT / "manuscript" / "_reference.docx"
POSTFMT = ROOT / "manuscript" / "postformat_docx.py"
OUTDIR = ROOT / "JECH submission"


def count_words(text):
    """Main-text word count: drop tables, captions, headings, and rules."""
    keep = [ln for ln in text.splitlines()
            if not ln.strip().startswith(("|", "**Table", "#", "---"))]
    t = "\n".join(keep)
    t = re.sub(r"[#*_`>|]", " ", t)
    t = re.sub(r"\^[0-9,\-]+\^", "", t)   # superscript citation markers
    t = re.sub(r"~[a-z0-9\-]+~", "", t)   # subscripts
    return len(t.split())


def to_docx(src_md, out_docx):
    subprocess.run(
        ["pandoc", str(src_md), "--reference-doc", str(REF),
         "--resource-path", ".", "-o", str(out_docx)],
        check=True, cwd=ROOT)
    subprocess.run([sys.executable, str(POSTFMT), str(out_docx)],
                   check=True, cwd=ROOT)


def build(outdir):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    # The rendered manuscript.md already carries the title, author block, and
    # word count (from build_manuscript.py), so it converts directly like the
    # other files — no separate title page is injected (that would duplicate the
    # author block and word count).
    for name in ("manuscript", "supplement", "strobe_checklist", "cover_letter"):
        to_docx(ROOT / "manuscript" / f"{name}.md", outdir / f"{name}.docx")
        print(f"  {name}.docx")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Build JECH submission DOCX files from rendered Markdown."
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=OUTDIR,
        help="Destination directory (defaults to 'JECH submission').",
    )
    args = parser.parse_args(argv)
    build(args.out_dir)


if __name__ == "__main__":
    main()
