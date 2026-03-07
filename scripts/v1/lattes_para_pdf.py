"""
lattes_para_pdf.py
==================
Converts a Lattes CV export (ZIP containing XML) into a professional PDF
curriculum vitae.  Runs entirely from the command line — no Jupyter, no
ipywidgets.

Usage
-----
    python lattes_para_pdf.py [ZIP_FILE] [--output OUTPUT_PDF]

    ZIP_FILE   : path to the .zip exported from the Lattes platform.
                 If omitted, the script searches the current directory
                 for the first *.zip it finds.
    --output   : optional explicit path for the generated PDF.
                 Defaults to <zip_stem>_cv.pdf beside the ZIP file.

Exit codes
----------
    0  — success
    1  — user / argument error
    2  — file / environment error
    3  — PDF generation error
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET
from html import unescape as _unescape


# ---------------------------------------------------------------------------
# 0. Dependency bootstrapping
# ---------------------------------------------------------------------------

_DEPS = ["reportlab>=4.0.0", "tqdm>=4.65.0"]


def _install_dependencies() -> None:
    """Install required packages if not already available."""
    print("Checking dependencies...")
    for pkg in _DEPS:
        pkg_name = pkg.split(">=")[0].split("==")[0]
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", pkg, "-q"],
            capture_output=True,
            text=True,
        )
        status = "ok" if result.returncode == 0 else "FAILED"
        print(f"  [{status}] {pkg_name}")
    print()


# ---------------------------------------------------------------------------
# 1. CLI argument parsing
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="lattes_para_pdf",
        description="Convert a Lattes XML ZIP export to a PDF curriculum vitae.",
    )
    parser.add_argument(
        "zip_file",
        nargs="?",
        default=None,
        metavar="ZIP_FILE",
        help="Path to the .zip exported from the Lattes platform. "
             "Auto-detected if omitted.",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        metavar="OUTPUT_PDF",
        help="Output PDF path. Defaults to <zip_stem>_cv.pdf.",
    )
    parser.add_argument(
        "--skip-deps",
        action="store_true",
        default=False,
        help="Skip automatic dependency installation.",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# 2. ZIP and XML resolution
# ---------------------------------------------------------------------------

def _resolve_zip(zip_arg: str | None) -> pathlib.Path:
    """Resolve the ZIP file path from argument or auto-detection."""
    if zip_arg:
        p = pathlib.Path(zip_arg)
        if not p.exists():
            print(f"Error: file not found: {p}", file=sys.stderr)
            sys.exit(1)
        return p.resolve()

    cwd = pathlib.Path.cwd()
    candidates = sorted(cwd.glob("*.zip"))
    if not candidates:
        print(f"Error: no .zip file found in '{cwd}'.", file=sys.stderr)
        sys.exit(2)
    chosen = candidates[0]
    print(f"ZIP auto-detected: {chosen.name}")
    return chosen


def _resolve_output(zip_path: pathlib.Path, output_arg: str | None) -> pathlib.Path:
    if output_arg:
        return pathlib.Path(output_arg).resolve()
    return zip_path.with_name(zip_path.stem + "_cv.pdf")


def _print_file_info(zip_path: pathlib.Path, pdf_path: pathlib.Path) -> None:
    size_kb = zip_path.stat().st_size / 1024
    print(f"  ZIP    : {zip_path}")
    print(f"  PDF    : {pdf_path}")
    print(f"  Size   : {size_kb:.1f} KB")
    print()


# ---------------------------------------------------------------------------
# 3. XML extraction and parsing
# ---------------------------------------------------------------------------

def extract_xml(zip_path: pathlib.Path) -> ET.Element:
    """Extract and parse the XML file from the Lattes ZIP archive."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        xml_names = [n for n in zf.namelist() if n.lower().endswith(".xml")]
        if not xml_names:
            print("Error: no XML file found inside the ZIP archive.", file=sys.stderr)
            sys.exit(2)
        with zf.open(xml_names[0]) as fh:
            raw = fh.read()

    try:
        return ET.fromstring(raw)
    except ET.ParseError:
        # Some Lattes exports carry an encoding declaration that confuses the
        # standard parser when the bytes are already decoded as UTF-8.
        cleaned = re.sub(rb'encoding=["\'][^"\']+["\']', b"", raw, count=1)
        return ET.fromstring(cleaned)


def _print_xml_info(root: ET.Element) -> None:
    print(f"  Root tag  : <{root.tag}>")
    print(f"  Lattes ID : {root.get('NUMERO-IDENTIFICADOR', 'N/A')}")
    print(f"  Updated   : {root.get('DATA-ATUALIZACAO', 'N/A')}")
    print()


# ---------------------------------------------------------------------------
# 4. XML helper utilities
# ---------------------------------------------------------------------------

def _attr(elem: ET.Element | None, key: str, default: str = "") -> str:
    if elem is None:
        return default
    val = elem.get(key, default)
    return _unescape(val).strip() if val else default


def _fmt_date(ddmmyyyy: str) -> str:
    d = ddmmyyyy.strip()
    return f"{d[0:2]}/{d[2:4]}/{d[4:8]}" if len(d) == 8 else d


def _period(yr_s: str, mo_s: str, yr_e: str, mo_e: str) -> str:
    """Build a human-readable period string, e.g. '04/2024 - Present'."""
    start = f"{mo_s}/{yr_s}" if mo_s else yr_s
    end   = (f"{mo_e}/{yr_e}" if mo_e else yr_e) if yr_e else "Present"
    return f"{start} - {end}"


# ---------------------------------------------------------------------------
# 5. Structured data extraction — one pure function per section
# ---------------------------------------------------------------------------

def extract_personal(root: ET.Element) -> dict:
    dg  = root.find("DADOS-GERAIS")
    if dg is None:
        return {}
    res  = dg.find("RESUMO-CV")
    out  = dg.find("OUTRAS-INFORMACOES-RELEVANTES")
    ep   = dg.find(".//ENDERECO-PROFISSIONAL")
    er   = dg.find(".//ENDERECO-RESIDENCIAL")
    email = _attr(ep, "E-MAIL") or _attr(er, "E-MAIL")
    return {
        "name"       : _attr(dg,  "NOME-COMPLETO"),
        "citation"   : _attr(dg,  "NOME-EM-CITACOES-BIBLIOGRAFICAS"),
        "birth"      : _fmt_date(_attr(dg, "DATA-NASCIMENTO")),
        "country"    : _attr(dg,  "PAIS-DE-NASCIMENTO"),
        "orcid"      : _attr(dg,  "ORCID-ID"),
        "email"      : email,
        "homepage"   : _attr(ep,  "HOME-PAGE") or _attr(dg, "HOME-PAGE"),
        "summary"    : _attr(res, "TEXTO-RESUMO-CV-RH")    if res is not None else "",
        "summary_en" : _attr(res, "TEXTO-RESUMO-CV-RH-EN") if res is not None else "",
        "other_info" : _attr(out, "OUTRAS-INFORMACOES-RELEVANTES") if out is not None else "",
    }


_DEGREE_TAGS = [
    ("DOUTORADO",               "NOME-CURSO", "Doctorate"),
    ("MESTRADO",                "NOME-CURSO", "Master's"),
    ("MESTRADO-PROFISSIONAL",   "NOME-CURSO", "Professional Master's"),
    ("ESPECIALIZACAO",          "NOME-CURSO", "Specialization"),
    ("GRADUACAO",               "NOME-CURSO", "Undergraduate"),
    ("APERFEICOAMENTO",         "NOME-CURSO", "Continuing Education / Extension"),
    ("ENSINO-MEDIO-SEGUNDO-GRAU",        "",  "High School"),
    ("ENSINO-FUNDAMENTAL-PRIMEIRO-GRAU", "",  "Primary School"),
]


def extract_education(root: ET.Element) -> list:
    sec = root.find(".//FORMACAO-ACADEMICA-TITULACAO")
    if sec is None:
        return []
    items: list = []
    for tag, course_key, label in _DEGREE_TAGS:
        for el in sec.findall(tag):
            course = _attr(el, course_key) if course_key else ""
            title  = (
                _attr(el, "TITULO-DA-MONOGRAFIA")
                or _attr(el, "TITULO-DO-TRABALHO-DE-CONCLUSAO-DE-CURSO")
            )
            status = _attr(el, "STATUS-DO-CURSO").replace("_", " ").capitalize()
            items.append({
                "type"       : label,
                "course"     : course,
                "institution": _attr(el, "NOME-INSTITUICAO"),
                "start"      : _attr(el, "ANO-DE-INICIO"),
                "end"        : _attr(el, "ANO-DE-CONCLUSAO") or "In progress",
                "status"     : status,
                "title"      : title,
                "workload"   : _attr(el, "CARGA-HORARIA"),
            })
    items.sort(key=lambda x: x["end"], reverse=True)
    return items


def extract_experience(root: ET.Element) -> list:
    sec = root.find(".//ATUACOES-PROFISSIONAIS")
    if sec is None:
        return []
    items: list = []
    seen: set   = set()
    for ap in sec.findall("ATUACAO-PROFISSIONAL"):
        inst = _attr(ap, "NOME-INSTITUICAO")
        for vt in ap.findall(".//VINCULOS"):
            role = (
                _attr(vt, "OUTRO-ENQUADRAMENTO-FUNCIONAL-INFORMADO")
                or _attr(vt, "OUTRO-VINCULO-INFORMADO")
                or _attr(vt, "TIPO-DE-VINCULO")
            )
            yr_s, mo_s = _attr(vt, "ANO-INICIO"), _attr(vt, "MES-INICIO")
            yr_e, mo_e = _attr(vt, "ANO-FIM"),    _attr(vt, "MES-FIM")
            desc = (
                _attr(vt, "OUTRAS-INFORMACOES-INGLES")
                or _attr(vt, "OUTRAS-INFORMACOES")
            )
            key = (inst, role, yr_s)
            if key in seen:
                continue
            seen.add(key)
            items.append({
                "institution": inst,
                "role"       : role,
                "period"     : _period(yr_s, mo_s, yr_e, mo_e),
                "description": desc,
            })
    items.sort(key=lambda x: x["period"], reverse=True)
    return items


def extract_internships(root: ET.Element) -> list:
    seen:  set  = set()
    items: list = []
    for el in root.findall(".//ESTAGIO"):
        inst     = _attr(el, "NOME-ORGAO")
        activity = _attr(el, "ESTAGIO-REALIZADO")
        key = (inst, activity)
        if key in seen:
            continue
        seen.add(key)
        items.append({
            "institution": inst,
            "activity"   : activity,
            "period"     : _period(
                _attr(el, "ANO-INICIO"), _attr(el, "MES-INICIO"),
                _attr(el, "ANO-FIM"),   _attr(el, "MES-FIM"),
            ),
        })
    return items


def extract_research(root: ET.Element) -> list:
    items: list = []
    for pd in root.findall(".//PESQUISA-E-DESENVOLVIMENTO"):
        org  = _attr(pd, "NOME-ORGAO")
        year = _attr(pd, "ANO-INICIO")
        seen_l: set = set()
        lines: list = []
        for ln in pd.findall("LINHA-DE-PESQUISA"):
            t = _attr(ln, "TITULO-DA-LINHA-DE-PESQUISA")
            if t and t not in seen_l:
                seen_l.add(t)
                lines.append(t)
        if org or lines:
            items.append({"org": org, "year": year, "lines": lines})
    return items


def extract_publications(root: ET.Element) -> list:
    sec = root.find(".//PRODUCAO-BIBLIOGRAFICA")
    if sec is None:
        return []
    items: list = []

    def _authors(el: ET.Element) -> str:
        return "; ".join(
            _attr(a, "NOME-COMPLETO-DO-AUTOR") for a in el.findall(".//AUTORES")
        )

    for el in sec.findall(".//ARTIGO-PUBLICADO"):
        d   = el.find("DADOS-BASICOS-DO-ARTIGO")
        if d is None:
            continue
        det = el.find("DETALHAMENTO-DO-ARTIGO")
        items.append({
            "type"   : "Journal Article",
            "title"  : _attr(d,   "TITULO-DO-ARTIGO"),
            "year"   : _attr(d,   "ANO-DO-ARTIGO"),
            "venue"  : _attr(det, "TITULO-DO-PERIODICO-OU-REVISTA") if det is not None else "",
            "authors": _authors(el),
            "doi"    : _attr(d,   "DOI"),
        })

    for el in sec.findall(".//LIVRO-PUBLICADO-OU-ORGANIZADO"):
        d = el.find("DADOS-BASICOS-DO-LIVRO")
        if d is None:
            continue
        items.append({
            "type": "Book", "title": _attr(d, "TITULO-DO-LIVRO"),
            "year": _attr(d, "ANO"), "venue": "",
            "authors": _authors(el), "doi": _attr(d, "DOI"),
        })

    for el in sec.findall(".//CAPITULO-DE-LIVRO-PUBLICADO"):
        d = el.find("DADOS-BASICOS-DO-CAPITULO")
        if d is None:
            continue
        items.append({
            "type": "Book Chapter",
            "title": _attr(d, "TITULO-DO-CAPITULO-DO-LIVRO"),
            "year" : _attr(d, "ANO"), "venue": "",
            "authors": _authors(el), "doi": _attr(d, "DOI"),
        })

    items.sort(key=lambda x: x.get("year", ""), reverse=True)
    return items


def extract_areas(root: ET.Element) -> list:
    """
    Searches recursively — tag location varies across Lattes XML versions.
    Attribute name fallbacks handle schema variants.
    """
    candidates = root.findall(".//AREA-DE-ATUACAO")
    if not candidates:
        return []
    _GRANDE = ["NOME-GRANDE-AREA-DO-CONHECIMENTO", "GRANDE-AREA"]
    _AREA   = ["NOME-DA-AREA-DO-CONHECIMENTO",     "AREA"]
    _ESPEC  = ["NOME-DA-ESPECIALIDADE",             "ESPECIALIDADE"]

    def _first(el: ET.Element, keys: list) -> str:
        for k in keys:
            v = _attr(el, k)
            if v:
                return v
        return ""

    areas: set = set()
    for el in candidates:
        parts = [p for p in [
            _first(el, _GRANDE),
            _first(el, _AREA),
            _first(el, _ESPEC),
        ] if p]
        if parts:
            areas.add(" > ".join(parts))
    return sorted(areas)


def extract_languages(root: ET.Element) -> list:
    sec = root.find(".//IDIOMAS")
    if sec is None:
        return []
    return [{
        "language": _attr(el, "IDIOMA"),
        "oral"    : _attr(el, "PROFICIENCIA-DE-CONVERSACAO"),
        "reading" : _attr(el, "PROFICIENCIA-DE-LEITURA"),
        "writing" : _attr(el, "PROFICIENCIA-DE-ESCRITA"),
    } for el in sec.findall("IDIOMA")]


def extract_awards(root: ET.Element) -> list:
    sec = root.find(".//PREMIOS-TITULOS")
    if sec is None:
        return []
    items = [{
        "name"  : _attr(el, "NOME-DO-PREMIO-OU-TITULO"),
        "year"  : _attr(el, "ANO-DA-PREMIACAO"),
        "entity": _attr(el, "NOME-DA-ENTIDADE-PROMOTORA"),
    } for el in sec.findall("PREMIO-TITULO")]
    items.sort(key=lambda x: x.get("year", ""), reverse=True)
    return items


def extract_events(root: ET.Element) -> list:
    items: list = []
    for el in root.findall(".//PARTICIPACAO-EM-CONGRESSO"):
        d   = el.find("DADOS-BASICOS-DA-PARTICIPACAO-EM-CONGRESSO")
        det = el.find("DETALHAMENTO-DA-PARTICIPACAO-EM-CONGRESSO")
        if d is None:
            continue
        items.append({
            "title"  : _attr(d,   "TITULO"),
            "year"   : _attr(d,   "ANO"),
            "event"  : _attr(det, "NOME-DO-EVENTO") if det is not None else "",
            "country": _attr(d,   "PAIS-DO-EVENTO"),
        })
    items.sort(key=lambda x: x.get("year", ""), reverse=True)
    return items


def extract_complementary_formation(root: ET.Element) -> list:
    """
    Extracts short-duration courses (FORMACAO-COMPLEMENTAR-CURSO-DE-CURTA-DURACAO)
    and university extension courses (FORMACAO-COMPLEMENTAR-DE-EXTENSAO-UNIVERSITARIA)
    from DADOS-COMPLEMENTARES/FORMACAO-COMPLEMENTAR.
    Both types are normalised to the same record schema and sorted by end year.
    """
    sec = root.find(".//FORMACAO-COMPLEMENTAR")
    if sec is None:
        return []
    items: list = []

    for el in sec.findall("FORMACAO-COMPLEMENTAR-CURSO-DE-CURTA-DURACAO"):
        items.append({
            "kind"       : "Short Course",
            "name"       : _attr(el, "NOME-CURSO-CURTA-DURACAO"),
            "institution": _attr(el, "NOME-INSTITUICAO"),
            "workload"   : _attr(el, "CARGA-HORARIA"),
            "start"      : _attr(el, "ANO-DE-INICIO"),
            "end"        : _attr(el, "ANO-DE-CONCLUSAO") or "In progress",
            "status"     : _attr(el, "STATUS-DO-CURSO").replace("_", " ").capitalize(),
        })

    for el in sec.findall("FORMACAO-COMPLEMENTAR-DE-EXTENSAO-UNIVERSITARIA"):
        items.append({
            "kind"       : "University Extension",
            "name"       : _attr(el, "NOME-CURSO-EXTENSAO-UNIVERSITARIA"),
            "institution": _attr(el, "NOME-INSTITUICAO"),
            "workload"   : _attr(el, "CARGA-HORARIA"),
            "start"      : _attr(el, "ANO-DE-INICIO"),
            "end"        : _attr(el, "ANO-DE-CONCLUSAO") or "In progress",
            "status"     : _attr(el, "STATUS-DO-CURSO").replace("_", " ").capitalize(),
        })

    items.sort(key=lambda x: x["end"], reverse=True)
    return items


def extract_work_presentations(root: ET.Element) -> list:
    """
    Extracts APRESENTACAO-DE-TRABALHO elements nested inside
    PARTICIPACAO-EM-CONGRESSO nodes (tag: PARTICIPACAO-EM-EVENTOS-CONGRESSOS).
    DADOS-BASICOS-DA-APRESENTACAO-DE-TRABALHO and the optional
    DETALHAMENTO-DA-APRESENTACAO-DE-TRABALHO sibling are both read.
    Deduplication key: (title, year).
    """
    items: list = []
    seen:  set  = set()

    for ap in root.findall(".//APRESENTACAO-DE-TRABALHO"):
        d   = ap.find("DADOS-BASICOS-DA-APRESENTACAO-DE-TRABALHO")
        det = ap.find("DETALHAMENTO-DA-APRESENTACAO-DE-TRABALHO")
        if d is None:
            continue
        title   = _attr(d, "TITULO")
        year    = _attr(d, "ANO")
        nature  = _attr(d, "NATUREZA").replace("_", " ").capitalize()
        country = _attr(d, "PAIS-DO-EVENTO")
        event   = _attr(det, "NOME-DO-EVENTO")  if det is not None else ""
        city    = _attr(det, "CIDADE-DO-EVENTO") if det is not None else ""
        key = (title, year)
        if key in seen:
            continue
        seen.add(key)
        items.append({
            "title"  : title,
            "year"   : year,
            "nature" : nature,
            "event"  : event,
            "city"   : city,
            "country": country,
        })

    items.sort(key=lambda x: x.get("year", ""), reverse=True)
    return items


def extract_additional_courses(root: ET.Element) -> list:
    """
    Searches the entire tree for INFORMACOES-ADICIONAIS-CURSO elements.
    These discipline-level records appear inside formation elements
    (GRADUACAO, MESTRADO, ESPECIALIZACAO, etc.) wrapped by
    INFORMACOES-ADICIONAIS-CURSOS.
    Deduplication key: (name, year, semester).
    Sorted by (year desc, semester desc).
    """
    seen:  set  = set()
    items: list = []

    for el in root.findall(".//INFORMACOES-ADICIONAIS-CURSO"):
        name     = _attr(el, "NOME-DISCIPLINA")
        year     = _attr(el, "ANO")
        semester = _attr(el, "SEMESTRE")
        status   = _attr(el, "SITUACAO").replace("_", " ").capitalize()
        wl_t     = _attr(el, "CARGA-HORARIA-TEORICA")
        wl_p     = _attr(el, "CARGA-HORARIA-PRATICA")
        workload = (
            f"{wl_t}h theory / {wl_p}h practice" if (wl_t and wl_p)
            else wl_t or wl_p
        )
        key = (name, year, semester)
        if key in seen:
            continue
        seen.add(key)
        items.append({
            "name"    : name,
            "year"    : year,
            "semester": semester,
            "status"  : status,
            "workload": workload,
        })

    items.sort(
        key=lambda x: (x.get("year", ""), x.get("semester", "")),
        reverse=True,
    )
    return items


def extract_additional_institutions(root: ET.Element) -> list:
    """
    Searches the entire tree for INFORMACOES-ADICIONAIS-INSTITUICAO elements.
    These provide enriched institutional metadata associated with professional
    activities (wrapped by INFORMACOES-ADICIONAIS-INSTITUICOES).
    Deduplication key: (institution name, department/organ name).
    """
    seen:  set  = set()
    items: list = []

    for el in root.findall(".//INFORMACOES-ADICIONAIS-INSTITUICAO"):
        name    = _attr(el, "NOME-INSTITUICAO")
        country = _attr(el, "PAIS-INSTITUICAO")
        state   = _attr(el, "UF-INSTITUICAO")
        org     = _attr(el, "NOME-ORGAO")
        if not name:
            continue
        key = (name, org)
        if key in seen:
            continue
        seen.add(key)
        items.append({
            "institution": name,
            "country"    : country,
            "state"      : state,
            "department" : org,
        })

    return items


# ---------------------------------------------------------------------------
# 6. Data extraction pipeline
# ---------------------------------------------------------------------------

_PIPELINE = [
    ("Personal data",              extract_personal),
    ("Academic background",        extract_education),
    ("Professional experience",    extract_experience),
    ("Internships",                extract_internships),
    ("Research activities",        extract_research),
    ("Publications",               extract_publications),
    ("Areas of expertise",         extract_areas),
    ("Languages",                  extract_languages),
    ("Awards",                     extract_awards),
    ("Events",                     extract_events),
    ("Complementary formation",    extract_complementary_formation),
    ("Work presentations",         extract_work_presentations),
    ("Additional courses",         extract_additional_courses),
    ("Additional institutions",    extract_additional_institutions),
]


def run_pipeline(root: ET.Element) -> dict:
    """Run all extraction functions and return a keyed data dict."""
    data: dict = {}
    total = len(_PIPELINE)
    for idx, (name, fn) in enumerate(_PIPELINE, start=1):
        print(f"  [{idx:02d}/{total}] {name}...", end="", flush=True)
        data[name] = fn(root)
        count = 1 if isinstance(data[name], dict) else len(data[name])
        print(f" {count} record(s)")
    return data


def _print_extraction_summary(data: dict) -> None:
    print("\nExtraction summary:")
    for k, v in data.items():
        n = 1 if isinstance(v, dict) else len(v)
        print(f"  {k:<30} {n} record(s)")
    print()


# ---------------------------------------------------------------------------
# 7. PDF generation — font registration
# ---------------------------------------------------------------------------

def _register_fonts() -> tuple[str, str, str]:
    """
    Register Times New Roman TTF variants for full Unicode support.
    Falls back to built-in ReportLab fonts on non-Windows systems.
    Returns (font_body, font_bold, font_italic).
    """
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase.pdfmetrics import registerFontFamily

    ttf_map = {
        "TNR"          : "C:/Windows/Fonts/times.ttf",
        "TNR-Bold"     : "C:/Windows/Fonts/timesbd.ttf",
        "TNR-Italic"   : "C:/Windows/Fonts/timesi.ttf",
        "TNR-BoldItalic": "C:/Windows/Fonts/timesbi.ttf",
    }

    n_reg = 0
    for alias, path in ttf_map.items():
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont(alias, path))
            n_reg += 1

    if n_reg >= 2:
        registerFontFamily(
            "TNR",
            normal="TNR",
            bold="TNR-Bold",
            italic="TNR-Italic",
            boldItalic="TNR-BoldItalic",
        )
        print(f"  Font: Times New Roman TTF registered ({n_reg} variants)")
        return "TNR", "TNR-Bold", "TNR-Italic"

    print("  Font: Windows TTF not found — using built-in ReportLab fonts")
    return "Times-Roman", "Times-Bold", "Times-Italic"


# ---------------------------------------------------------------------------
# 8. PDF style system
# ---------------------------------------------------------------------------

def _build_styles(font_body: str, font_bold: str, font_italic: str) -> dict:
    from reportlab.lib.pagesizes import A4          # noqa: F401 (used by caller)
    from reportlab.lib.enums     import TA_CENTER, TA_LEFT, TA_JUSTIFY
    from reportlab.lib           import colors
    from reportlab.lib.styles    import ParagraphStyle

    blue  = colors.HexColor("#1a3557")
    gray  = colors.HexColor("#555555")
    line  = colors.HexColor("#b0b8c8")   # stored for caller use via styles dict
    strip = colors.HexColor("#f4f6fa")

    _base = dict(fontName=font_body, fontSize=10, leading=14, textColor=colors.black)
    _bold = dict(fontName=font_bold, fontSize=10, leading=14, textColor=colors.black)

    return {
        "_blue" : blue,
        "_gray" : gray,
        "_line" : line,
        "_strip": strip,
        "name"    : ParagraphStyle("name",    alignment=TA_CENTER, fontSize=20, leading=26,
                                   fontName=font_bold,   textColor=blue),
        "subtitle": ParagraphStyle("subtitle", alignment=TA_CENTER, fontSize=10, leading=14,
                                   fontName=font_italic, textColor=gray),
        "meta"    : ParagraphStyle("meta",    alignment=TA_CENTER, fontSize=9,  leading=12,
                                   fontName=font_body,   textColor=gray),
        "section" : ParagraphStyle("section", alignment=TA_CENTER, fontSize=13, leading=18,
                                   fontName=font_bold,   textColor=blue, spaceAfter=2),
        "body"    : ParagraphStyle("body",    alignment=TA_JUSTIFY, **_base,    spaceAfter=2),
        "small"   : ParagraphStyle("small",   alignment=TA_LEFT,   fontSize=9,  leading=12,
                                   fontName=font_body,   textColor=gray),
        "bullet"  : ParagraphStyle("bullet",  alignment=TA_LEFT,   **_base,
                                   leftIndent=14, bulletIndent=4, spaceAfter=1),
    }


# ---------------------------------------------------------------------------
# 9. Layout primitives
# ---------------------------------------------------------------------------
#
# ENCODING STRATEGY (critical for Unicode/accents):
#   ReportLab Paragraph parses content as XML. Two rules must hold:
#   1. XML special chars (&, <, >) must be escaped.
#   2. With a TTF font registered, Python UTF-8 strings render natively.
#      Do NOT convert to &#nnn; -- that can cause double-escape.
#
#   _p(text)   : plain text  -> calls _safe() once -> Paragraph
#   _pm(markup): pre-escaped markup (<b>, <i>) -> Paragraph directly
#   Use _pm(f"<b>{_safe(t)}</b>") for bold. NEVER _p(f"<b>...").
# ---------------------------------------------------------------------------

def _safe(text: str) -> str:
    """Escape XML meta-characters. UTF-8 chars pass through for TTF rendering."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _make_primitives(ST: dict):
    """Return layout primitive callables bound to a style dict ST."""
    from reportlab.platypus import Paragraph, Spacer, HRFlowable
    from reportlab.lib.units import cm

    line_color = ST["_line"]

    def _p(text: str, style: str = "body") -> Paragraph:
        return Paragraph(_safe(text), ST[style])

    def _pm(markup: str, style: str = "body") -> Paragraph:
        return Paragraph(markup, ST[style])

    def _b(text: str) -> Paragraph:
        return Paragraph(f"&#8226; {_safe(text)}", ST["bullet"])

    def _hr() -> HRFlowable:
        return HRFlowable(width="100%", thickness=0.8, color=line_color,
                          spaceAfter=4, spaceBefore=4)

    def _sp(h: float = 0.3) -> Spacer:
        return Spacer(1, h * cm)

    def _section_header(title: str) -> list:
        return [_sp(0.25), _hr(), _p(title.upper(), "section"), _hr(), _sp(0.1)]

    return _p, _pm, _b, _hr, _sp, _section_header


# ---------------------------------------------------------------------------
# 10. Section builders
# ---------------------------------------------------------------------------

def _make_builders(ST: dict, font_body: str, font_bold: str):
    """Return section builder callables bound to the current style and font set."""
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors

    _p, _pm, _b, _hr, _sp, _section_header = _make_primitives(ST)

    blue  = ST["_blue"]
    line  = ST["_line"]
    strip = ST["_strip"]

    def build_header(p: dict) -> list:
        story = [_p(p.get("name", ""), "name")]
        if p.get("citation"):
            story.append(_p(f"Bibliographic citation: {p['citation']}", "subtitle"))
        meta = []
        if p.get("birth"):    meta.append(f"Date of birth: {p['birth']}")
        if p.get("country"):  meta.append(f"Country: {p['country']}")
        if p.get("orcid"):    meta.append(f"ORCID: {p['orcid']}")
        if p.get("email"):    meta.append(f"Email: {p['email']}")
        if p.get("homepage"): meta.append(f"Web: {p['homepage']}")
        if meta:
            story.append(_p("  |  ".join(meta), "meta"))
        story.append(_sp(0.4))
        return story

    def build_summary(p: dict) -> list:
        text = p.get("summary_en") or p.get("summary", "")
        if not text.strip():
            return []
        return _section_header("Summary") + [_p(text), _sp()]

    def build_education(items: list) -> list:
        if not items:
            return []
        story = _section_header("Academic Background")
        for it in items:
            label = it["type"]
            if it["course"]:
                label += f" in {it['course']}"
            story.append(_pm(f"<b>{_safe(label)}</b>", "body"))
            period = f"{it['start']} - {it['end']}"
            story.append(_p(f"{it['institution']}  |  {period}  |  {it['status']}", "small"))
            if it.get("title"):
                story.append(_p(f"Thesis/Project: {it['title']}", "small"))
            if it.get("workload"):
                story.append(_p(f"Workload: {it['workload']} h", "small"))
            story.append(_sp(0.2))
        return story

    def build_experience(items: list) -> list:
        if not items:
            return []
        story = _section_header("Professional Experience")
        for it in items:
            story.append(_pm(f"<b>{_safe(it['role'])}</b>", "body"))
            story.append(_p(f"{it['institution']}  |  {it['period']}", "small"))
            if it.get("description"):
                desc = it["description"]
                if len(desc) > 700:
                    desc = desc[:700] + "..."
                story.append(_p(desc))
            story.append(_sp(0.2))
        return story

    def build_internships(items: list) -> list:
        if not items:
            return []
        story = _section_header("Internships")
        for it in items:
            story.append(_b(f"{it['activity']}  -  {it['institution']}  |  {it['period']}"))
        story.append(_sp())
        return story

    def build_research(items: list) -> list:
        if not items:
            return []
        story = _section_header("Research and Development Activities")
        for it in items:
            label = it["org"]
            if it.get("year"):
                label += f"  ({it['year']})"
            story.append(_pm(f"<b>{_safe(label)}</b>", "body"))
            for ln in it["lines"][:8]:
                story.append(_b(ln))
            story.append(_sp(0.15))
        return story

    def build_publications(items: list) -> list:
        if not items:
            return []
        story = _section_header("Bibliographic Production")
        for it in items:
            parts = [f"[{it['year']}] {it['title']}"]
            if it.get("venue"):   parts.append(it["venue"])
            if it.get("authors"): parts.append(f"Authors: {it['authors']}")
            if it.get("doi"):     parts.append(f"DOI: {it['doi']}")
            story.append(_b("  |  ".join(parts)))
        story.append(_sp())
        return story

    def build_areas(items: list) -> list:
        if not items:
            return []
        return _section_header("Areas of Expertise") + [_b(a) for a in items] + [_sp()]

    def build_languages(items: list) -> list:
        if not items:
            return []
        story = _section_header("Languages")
        rows = [["Language", "Speaking", "Reading", "Writing"]] + [
            [it["language"], it["oral"], it["reading"], it["writing"]]
            for it in items
        ]
        t = Table(rows, colWidths=[4 * cm, 4 * cm, 4 * cm, 4 * cm])
        t.setStyle(TableStyle([
            ("FONTNAME",       (0, 0), (-1,  0), font_bold),
            ("FONTNAME",       (0, 1), (-1, -1), font_body),
            ("FONTSIZE",       (0, 0), (-1, -1), 9),
            ("ALIGN",          (0, 0), (-1, -1), "CENTER"),
            ("GRID",           (0, 0), (-1, -1), 0.5, line),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, strip]),
            ("TEXTCOLOR",      (0, 0), (-1,  0), blue),
        ]))
        story.append(t)
        story.append(_sp())
        return story

    def build_awards(items: list) -> list:
        if not items:
            return []
        story = _section_header("Awards and Titles")
        for it in items:
            line_text = it["name"]
            if it.get("entity"): line_text += f"  -  {it['entity']}"
            if it.get("year"):   line_text += f"  ({it['year']})"
            story.append(_b(line_text))
        story.append(_sp())
        return story

    def build_events(items: list) -> list:
        if not items:
            return []
        story = _section_header("Conference and Event Participation")
        for it in items:
            line_text = f"[{it.get('year', '?')}] {it.get('title', '')}"
            if it.get("event"):   line_text += f"  -  {it['event']}"
            if it.get("country"): line_text += f"  ({it['country']})"
            story.append(_b(line_text))
        story.append(_sp())
        return story

    def build_complementary_formation(items: list) -> list:
        if not items:
            return []
        story = _section_header("Complementary Formation")
        for it in items:
            label = f"{it['kind']}: {it['name']}" if it.get("kind") else it.get("name", "")
            story.append(_pm(f"<b>{_safe(label)}</b>", "body"))
            parts: list = []
            if it.get("institution"): parts.append(it["institution"])
            period = f"{it['start']} - {it['end']}" if it.get("start") else it.get("end", "")
            if period:               parts.append(period)
            if it.get("status"):     parts.append(it["status"])
            if it.get("workload"):   parts.append(f"{it['workload']} h")
            if parts:
                story.append(_p("  |  ".join(parts), "small"))
            story.append(_sp(0.2))
        return story

    def build_work_presentations(items: list) -> list:
        if not items:
            return []
        story = _section_header("Work Presentations")
        for it in items:
            line_text = f"[{it.get('year', '?')}] {it.get('title', '')}"
            if it.get("nature"):  line_text += f"  ({it['nature']})"
            if it.get("event"):   line_text += f"  -  {it['event']}"
            if it.get("city"):    line_text += f", {it['city']}"
            if it.get("country"): line_text += f"  ({it['country']})"
            story.append(_b(line_text))
        story.append(_sp())
        return story

    def build_additional_courses(items: list) -> list:
        if not items:
            return []
        story = _section_header("Coursework Details")
        for it in items:
            story.append(_pm(f"<b>{_safe(it.get('name', ''))}</b>", "body"))
            parts: list = []
            period_str = it.get("year", "")
            if period_str and it.get("semester"):
                period_str += f" / Semester {it['semester']}"
            if period_str:           parts.append(period_str)
            if it.get("status"):     parts.append(it["status"])
            if it.get("workload"):   parts.append(it["workload"])
            if parts:
                story.append(_p("  |  ".join(parts), "small"))
            story.append(_sp(0.15))
        return story

    def build_additional_institutions(items: list) -> list:
        if not items:
            return []
        story = _section_header("Institutional References")
        for it in items:
            story.append(_pm(f"<b>{_safe(it.get('institution', ''))}</b>", "body"))
            parts: list = []
            if it.get("department"): parts.append(it["department"])
            if it.get("state"):      parts.append(it["state"])
            if it.get("country"):    parts.append(it["country"])
            if parts:
                story.append(_p("  |  ".join(parts), "small"))
            story.append(_sp(0.15))
        return story

    return (
        build_header, build_summary, build_education, build_experience,
        build_internships, build_research, build_publications,
        build_areas, build_languages, build_awards, build_events,
        build_complementary_formation, build_work_presentations,
        build_additional_courses, build_additional_institutions,
    )


# ---------------------------------------------------------------------------
# 11. Document assembly and PDF generation
# ---------------------------------------------------------------------------

def generate_pdf(
    pdf_path: pathlib.Path,
    data: dict,
    font_body: str,
    font_bold: str,
    font_italic: str,
    ST: dict,
) -> None:
    """Assemble all sections and write the final PDF to disk."""
    from reportlab.platypus  import SimpleDocTemplate
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units     import cm

    personal               = data["Personal data"]
    education              = data["Academic background"]
    experience             = data["Professional experience"]
    internships            = data["Internships"]
    research               = data["Research activities"]
    publications           = data["Publications"]
    areas                  = data["Areas of expertise"]
    languages              = data["Languages"]
    awards                 = data["Awards"]
    events                 = data["Events"]
    complementary          = data["Complementary formation"]
    work_presentations     = data["Work presentations"]
    additional_courses     = data["Additional courses"]
    additional_institutions = data["Additional institutions"]

    (
        build_header, build_summary, build_education, build_experience,
        build_internships, build_research, build_publications,
        build_areas, build_languages, build_awards, build_events,
        build_complementary_formation, build_work_presentations,
        build_additional_courses, build_additional_institutions,
    ) = _make_builders(ST, font_body, font_bold)

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        topMargin=2.2 * cm,  bottomMargin=2.2 * cm,
        leftMargin=2.5 * cm, rightMargin=2.5 * cm,
        title=f"Curriculum Vitae - {personal.get('name', '')}",
        author="Lattes XML to PDF Converter",
        subject="Academic Curriculum Vitae",
    )

    story: list = []
    story += build_header(personal)
    story += build_summary(personal)
    story += build_areas(areas)
    story += build_education(education)
    story += build_complementary_formation(complementary)
    story += build_experience(experience)
    story += build_internships(internships)
    story += build_research(research)
    story += build_work_presentations(work_presentations)
    story += build_publications(publications)
    story += build_awards(awards)
    story += build_events(events)
    story += build_additional_courses(additional_courses)
    story += build_additional_institutions(additional_institutions)
    story += build_languages(languages)

    doc.build(story)


# ---------------------------------------------------------------------------
# 12. Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    args = _parse_args()

    if not args.skip_deps:
        _install_dependencies()

    # Import reportlab only after potential installation
    zip_path = _resolve_zip(args.zip_file)
    pdf_path = _resolve_output(zip_path, args.output)

    print("File information:")
    _print_file_info(zip_path, pdf_path)

    print("Extracting XML from ZIP...")
    try:
        root = extract_xml(zip_path)
    except Exception as exc:
        print(f"Error: XML extraction failed: {exc}", file=sys.stderr)
        sys.exit(2)

    print("XML information:")
    _print_xml_info(root)

    print("Extracting data from Lattes XML:")
    data = run_pipeline(root)
    _print_extraction_summary(data)

    print("Initializing PDF renderer...")
    try:
        font_body, font_bold, font_italic = _register_fonts()
        ST = _build_styles(font_body, font_bold, font_italic)
        print()
    except Exception as exc:
        print(f"Error: PDF renderer initialization failed: {exc}", file=sys.stderr)
        sys.exit(3)

    print("Generating PDF...")
    try:
        generate_pdf(pdf_path, data, font_body, font_bold, font_italic, ST)
    except Exception as exc:
        print(f"Error: PDF generation failed: {exc}", file=sys.stderr)
        sys.exit(3)

    size_kb = pdf_path.stat().st_size / 1024
    print(f"\nPDF generated successfully.")
    print(f"  File : {pdf_path}")
    print(f"  Size : {size_kb:.1f} KB")


if __name__ == "__main__":
    main()
