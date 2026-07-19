"""Renders CVContent / CoverLetterContent into .tex source via Jinja2 templates,
then compiles to PDF with pdflatex/xelatex if available on the system. If no
LaTeX distribution is found, the .tex file is still produced (and can be
compiled later, or pasted into Overleaf) — we never silently drop output."""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader

from app.config import settings
from app.models import CoverLetterContent, CVContent

TEMPLATES_DIR = Path(__file__).parent / "templates"

# Custom delimiters so Jinja doesn't collide with LaTeX's own {curly braces}.
_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    variable_start_string="\\VAR{",
    variable_end_string="}",
    block_start_string="\\BLOCK{",
    block_end_string="}",
    comment_start_string="\\#{",
    comment_end_string="}",
    trim_blocks=True,
    lstrip_blocks=True,
)

_LATEX_SPECIAL = {
    "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
    "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    "\\": r"\textbackslash{}",
}
_LATEX_RE = re.compile("|".join(re.escape(k) for k in _LATEX_SPECIAL))


def _esc(value):
    """Escape LaTeX special characters. Applied recursively to strings/lists."""
    if value is None:
        return ""
    if isinstance(value, str):
        return _LATEX_RE.sub(lambda m: _LATEX_SPECIAL[m.group(0)], value)
    if isinstance(value, list):
        return [_esc(v) for v in value]
    if isinstance(value, dict):
        return {k: _esc(v) for k, v in value.items()}
    return value


def _find_latex_binary(name: str) -> Optional[str]:
    if settings.latex_bin_dir:
        candidate = Path(settings.latex_bin_dir) / name
        if candidate.exists():
            return str(candidate)
    return shutil.which(name)


def _compile_pdf(tex_path: Path) -> Optional[Path]:
    binary = _find_latex_binary("pdflatex") or _find_latex_binary("xelatex")
    if not binary:
        return None
    try:
        # Run twice for stable hyperref/reference resolution; harmless if unneeded.
        for _ in range(2):
            subprocess.run(
                [binary, "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
                cwd=str(tex_path.parent),
                check=True,
                capture_output=True,
                timeout=60,
            )
        pdf_path = tex_path.with_suffix(".pdf")
        return pdf_path if pdf_path.exists() else None
    except Exception:
        return None


def _escape_cv(cv: CVContent) -> dict:
    contact_bits = [b for b in [cv.location, cv.email, cv.phone, *cv.links] if b]
    data = cv.model_dump()
    data["contact_line"] = " | ".join(contact_bits)
    return _esc(data)


def _escape_letter(letter: CoverLetterContent) -> dict:
    return _esc(letter.model_dump())


def render_cv_latex(cv: CVContent, out_dir: Path, basename: str = "cv") -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    template = _env.get_template("cv_template.tex.j2")
    tex_source = template.render(**_escape_cv(cv))
    tex_path = out_dir / f"{basename}.tex"
    tex_path.write_text(tex_source, encoding="utf-8")
    pdf_path = _compile_pdf(tex_path)
    return {"tex_path": tex_path, "pdf_path": pdf_path}


def render_cover_letter_latex(letter: CoverLetterContent, out_dir: Path, basename: str = "cover_letter") -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    template = _env.get_template("cover_letter_template.tex.j2")
    tex_source = template.render(**_escape_letter(letter))
    tex_path = out_dir / f"{basename}.tex"
    tex_path.write_text(tex_source, encoding="utf-8")
    pdf_path = _compile_pdf(tex_path)
    return {"tex_path": tex_path, "pdf_path": pdf_path}
