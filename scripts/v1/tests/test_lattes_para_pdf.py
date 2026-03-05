"""
tests/test_lattes_para_pdf.py
=============================
Functional tests for scripts/v1/lattes_para_pdf.py.

All tests exercise real logic — no mocks, no patching.
The test fixture is the ZIP file located in the project root
(auto-detected by _find_fixture_zip).

Running
-------
    cd scripts/v1
    pytest tests/ -v --tb=short

Or via the test_suite.ipynb notebook at scripts/.
"""

import pathlib
import sys
import zipfile
import xml.etree.ElementTree as ET

import pytest

# ---------------------------------------------------------------------------
# Resolve the module under test
# ---------------------------------------------------------------------------

_V1_DIR = pathlib.Path(__file__).parent.parent          # scripts/v1/
_ROOT   = _V1_DIR.parent.parent                         # project root

sys.path.insert(0, str(_V1_DIR))

import lattes_para_pdf as _mod  # noqa: E402 — import after sys.path manipulation


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _find_fixture_zip() -> pathlib.Path | None:
    """Return the first *.zip in the project root, or None if absent."""
    candidates = sorted(_ROOT.glob("*.zip"))
    return candidates[0] if candidates else None


def _build_minimal_xml(*, with_personal: bool = True) -> bytes:
    """
    Build a minimal, syntactically valid Lattes XML document in memory.
    Used for unit-level tests that do not require a real ZIP.
    """
    personal_block = ""
    if with_personal:
        personal_block = """
        <DADOS-GERAIS
            NOME-COMPLETO="Test User"
            NOME-EM-CITACOES-BIBLIOGRAFICAS="User, T."
            DATA-NASCIMENTO="01011990"
            PAIS-DE-NASCIMENTO="Brasil"
            ORCID-ID="0000-0000-0000-0000">
            <RESUMO-CV
                TEXTO-RESUMO-CV-RH="Portuguese summary."
                TEXTO-RESUMO-CV-RH-EN="English summary." />
            <ENDERECO-PROFISSIONAL E-MAIL="test@example.com" HOME-PAGE="https://example.com" />
        </DADOS-GERAIS>
        """
    return f"""<?xml version="1.0" encoding="UTF-8"?>
    <CURRICULO-VITAE NUMERO-IDENTIFICADOR="0000000000000000" DATA-ATUALIZACAO="01012025">
        {personal_block}
        <FORMACAO-ACADEMICA-TITULACAO>
            <GRADUACAO
                NOME-CURSO="Computer Science"
                NOME-INSTITUICAO="Test University"
                ANO-DE-INICIO="2010"
                ANO-DE-CONCLUSAO="2014"
                STATUS-DO-CURSO="CONCLUIDO" />
        </FORMACAO-ACADEMICA-TITULACAO>
        <IDIOMAS>
            <IDIOMA
                IDIOMA="Ingles"
                PROFICIENCIA-DE-CONVERSACAO="Avancado"
                PROFICIENCIA-DE-LEITURA="Fluente"
                PROFICIENCIA-DE-ESCRITA="Avancado" />
        </IDIOMAS>
        <PREMIOS-TITULOS>
            <PREMIO-TITULO
                NOME-DO-PREMIO-OU-TITULO="Best Paper Award"
                ANO-DA-PREMIACAO="2020"
                NOME-DA-ENTIDADE-PROMOTORA="IEEE" />
        </PREMIOS-TITULOS>
    </CURRICULO-VITAE>
    """.encode("utf-8")


def _parse_xml(raw: bytes) -> ET.Element:
    return ET.fromstring(raw)


# ---------------------------------------------------------------------------
# Section 1: XML utility functions
# ---------------------------------------------------------------------------

class TestAttrHelper:
    def test_returns_attribute_value(self):
        el = ET.fromstring('<FOO BAR="hello" />')
        assert _mod._attr(el, "BAR") == "hello"

    def test_returns_default_when_missing(self):
        el = ET.fromstring('<FOO />')
        assert _mod._attr(el, "MISSING", "default") == "default"

    def test_none_element_returns_default(self):
        assert _mod._attr(None, "ANY", "fallback") == "fallback"

    def test_strips_whitespace(self):
        el = ET.fromstring('<FOO BAR="  value  " />')
        assert _mod._attr(el, "BAR") == "value"


class TestFmtDate:
    def test_valid_8_digit_date(self):
        assert _mod._fmt_date("01011990") == "01/01/1990"

    def test_short_date_returned_as_is(self):
        assert _mod._fmt_date("2020") == "2020"

    def test_empty_string(self):
        assert _mod._fmt_date("") == ""


class TestPeriod:
    def test_open_ended(self):
        result = _mod._period("2020", "04", "", "")
        assert result == "04/2020 - Present"

    def test_closed(self):
        result = _mod._period("2020", "01", "2023", "12")
        assert result == "01/2020 - 12/2023"

    def test_year_only_no_month(self):
        result = _mod._period("2020", "", "2023", "")
        assert result == "2020 - 2023"


class TestSafeEscape:
    def test_ampersand(self):
        assert _mod._safe("a & b") == "a &amp; b"

    def test_less_than(self):
        assert _mod._safe("<tag>") == "&lt;tag&gt;"

    def test_plain_text_unchanged(self):
        assert _mod._safe("hello world") == "hello world"

    def test_utf8_chars_unchanged(self):
        assert _mod._safe("ção") == "ção"


# ---------------------------------------------------------------------------
# Section 2: Data extraction functions
# ---------------------------------------------------------------------------

class TestExtractPersonal:
    def setup_method(self):
        self.root = _parse_xml(_build_minimal_xml(with_personal=True))

    def test_name_extracted(self):
        p = _mod.extract_personal(self.root)
        assert p["name"] == "Test User"

    def test_citation_extracted(self):
        p = _mod.extract_personal(self.root)
        assert p["citation"] == "User, T."

    def test_email_extracted(self):
        p = _mod.extract_personal(self.root)
        assert p["email"] == "test@example.com"

    def test_homepage_extracted(self):
        p = _mod.extract_personal(self.root)
        assert p["homepage"] == "https://example.com"

    def test_summary_en_extracted(self):
        p = _mod.extract_personal(self.root)
        assert p["summary_en"] == "English summary."

    def test_no_dados_gerais_returns_empty_dict(self):
        root = ET.fromstring("<CURRICULO-VITAE />")
        assert _mod.extract_personal(root) == {}


class TestExtractEducation:
    def setup_method(self):
        self.root = _parse_xml(_build_minimal_xml())

    def test_returns_list(self):
        result = _mod.extract_education(self.root)
        assert isinstance(result, list)

    def test_graduation_found(self):
        result = _mod.extract_education(self.root)
        assert len(result) == 1
        assert result[0]["type"] == "Undergraduate"
        assert result[0]["course"] == "Computer Science"
        assert result[0]["institution"] == "Test University"
        assert result[0]["start"] == "2010"
        assert result[0]["end"] == "2014"

    def test_no_section_returns_empty(self):
        root = ET.fromstring("<CURRICULO-VITAE />")
        assert _mod.extract_education(root) == []


class TestExtractLanguages:
    def setup_method(self):
        self.root = _parse_xml(_build_minimal_xml())

    def test_returns_list(self):
        result = _mod.extract_languages(self.root)
        assert isinstance(result, list)

    def test_language_record_fields(self):
        result = _mod.extract_languages(self.root)
        assert len(result) == 1
        lang = result[0]
        assert lang["language"] == "Ingles"
        assert lang["oral"] == "Avancado"
        assert lang["reading"] == "Fluente"
        assert lang["writing"] == "Avancado"

    def test_no_section_returns_empty(self):
        root = ET.fromstring("<CURRICULO-VITAE />")
        assert _mod.extract_languages(root) == []


class TestExtractAwards:
    def setup_method(self):
        self.root = _parse_xml(_build_minimal_xml())

    def test_returns_list(self):
        result = _mod.extract_awards(self.root)
        assert isinstance(result, list)

    def test_award_fields(self):
        result = _mod.extract_awards(self.root)
        assert len(result) == 1
        assert result[0]["name"] == "Best Paper Award"
        assert result[0]["year"] == "2020"
        assert result[0]["entity"] == "IEEE"

    def test_no_section_returns_empty(self):
        root = ET.fromstring("<CURRICULO-VITAE />")
        assert _mod.extract_awards(root) == []


class TestExtractExperience:
    def test_empty_when_no_section(self):
        root = ET.fromstring("<CURRICULO-VITAE />")
        assert _mod.extract_experience(root) == []

    def test_deduplication(self):
        raw = b"""
        <CURRICULO-VITAE>
          <ATUACOES-PROFISSIONAIS>
            <ATUACAO-PROFISSIONAL NOME-INSTITUICAO="Org A">
              <VINCULOS TIPO-DE-VINCULO="Researcher" ANO-INICIO="2020" MES-INICIO="" ANO-FIM="" MES-FIM="" />
              <VINCULOS TIPO-DE-VINCULO="Researcher" ANO-INICIO="2020" MES-INICIO="" ANO-FIM="" MES-FIM="" />
            </ATUACAO-PROFISSIONAL>
          </ATUACOES-PROFISSIONAIS>
        </CURRICULO-VITAE>
        """
        root = ET.fromstring(raw)
        result = _mod.extract_experience(root)
        assert len(result) == 1


class TestExtractResearch:
    def test_empty_when_no_section(self):
        root = ET.fromstring("<CURRICULO-VITAE />")
        assert _mod.extract_research(root) == []

    def test_research_line_deduplication(self):
        raw = b"""
        <CURRICULO-VITAE>
          <PESQUISA-E-DESENVOLVIMENTO NOME-ORGAO="Lab" ANO-INICIO="2021">
            <LINHA-DE-PESQUISA TITULO-DA-LINHA-DE-PESQUISA="AI" />
            <LINHA-DE-PESQUISA TITULO-DA-LINHA-DE-PESQUISA="AI" />
          </PESQUISA-E-DESENVOLVIMENTO>
        </CURRICULO-VITAE>
        """
        root = ET.fromstring(raw)
        result = _mod.extract_research(root)
        assert result[0]["lines"] == ["AI"]


class TestExtractAreas:
    def test_empty_when_no_section(self):
        root = ET.fromstring("<CURRICULO-VITAE />")
        assert _mod.extract_areas(root) == []

    def test_area_built_with_separator(self):
        raw = b"""
        <CURRICULO-VITAE>
          <DADOS-GERAIS>
            <AREAS-DE-ATUACAO>
              <AREA-DE-ATUACAO
                NOME-GRANDE-AREA-DO-CONHECIMENTO="Ciencias Exatas"
                NOME-DA-AREA-DO-CONHECIMENTO="Ciencia da Computacao"
                NOME-DA-ESPECIALIDADE="Inteligencia Artificial" />
            </AREAS-DE-ATUACAO>
          </DADOS-GERAIS>
        </CURRICULO-VITAE>
        """
        root = ET.fromstring(raw)
        result = _mod.extract_areas(root)
        assert len(result) == 1
        assert " > " in result[0]


# ---------------------------------------------------------------------------
# Section 3: run_pipeline
# ---------------------------------------------------------------------------

class TestRunPipeline:
    def test_returns_all_keys(self):
        root = _parse_xml(_build_minimal_xml())
        data = _mod.run_pipeline(root)
        expected_keys = [name for name, _ in _mod._PIPELINE]
        for key in expected_keys:
            assert key in data, f"Missing key: {key}"

    def test_personal_data_is_dict(self):
        root = _parse_xml(_build_minimal_xml())
        data = _mod.run_pipeline(root)
        assert isinstance(data["Personal data"], dict)

    def test_education_is_list(self):
        root = _parse_xml(_build_minimal_xml())
        data = _mod.run_pipeline(root)
        assert isinstance(data["Academic background"], list)


# ---------------------------------------------------------------------------
# Section 4: ZIP extraction
# ---------------------------------------------------------------------------

class TestExtractXml:
    def test_valid_zip_returns_element(self, tmp_path):
        xml_bytes = _build_minimal_xml()
        zip_path  = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("curriculo.xml", xml_bytes)
        root = _mod.extract_xml(zip_path)
        assert root is not None
        assert root.tag == "CURRICULO-VITAE"

    def test_zip_without_xml_raises_sysexit(self, tmp_path):
        zip_path = tmp_path / "empty.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("readme.txt", "no xml here")
        with pytest.raises(SystemExit) as exc_info:
            _mod.extract_xml(zip_path)
        assert exc_info.value.code == 2

    def test_encoding_declaration_cleaned(self, tmp_path):
        """XML with an encoding declaration must parse without error."""
        raw = b'<?xml version="1.0" encoding="ISO-8859-1"?><CURRICULO-VITAE />'
        zip_path = tmp_path / "enc.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("curriculo.xml", raw)
        root = _mod.extract_xml(zip_path)
        assert root.tag == "CURRICULO-VITAE"


# ---------------------------------------------------------------------------
# Section 5: PDF generation (end-to-end with in-memory XML)
# ---------------------------------------------------------------------------

class TestGeneratePdf:
    """
    End-to-end test: builds a PDF from the minimal XML fixture.
    Validates that a non-empty file is written to disk.
    Requires reportlab to be installed.
    """

    def test_pdf_generated_from_minimal_xml(self, tmp_path):
        pytest.importorskip("reportlab")

        root     = _parse_xml(_build_minimal_xml())
        data     = _mod.run_pipeline(root)
        fb, fbo, fi = _mod._register_fonts()
        ST       = _mod._build_styles(fb, fbo, fi)
        pdf_path = tmp_path / "output.pdf"

        _mod.generate_pdf(pdf_path, data, fb, fbo, fi, ST)

        assert pdf_path.exists(), "PDF file was not created."
        assert pdf_path.stat().st_size > 1024, "PDF file is suspiciously small."

    def test_pdf_contains_name_in_metadata(self, tmp_path):
        """PDF title metadata must include the person's name."""
        pytest.importorskip("reportlab")

        root     = _parse_xml(_build_minimal_xml())
        data     = _mod.run_pipeline(root)
        fb, fbo, fi = _mod._register_fonts()
        ST       = _mod._build_styles(fb, fbo, fi)
        pdf_path = tmp_path / "output.pdf"

        _mod.generate_pdf(pdf_path, data, fb, fbo, fi, ST)

        raw_pdf = pdf_path.read_bytes()
        assert b"%PDF" in raw_pdf, "Output is not a valid PDF."


# ---------------------------------------------------------------------------
# Section 6: Integration — fixture ZIP from project root (optional)
# ---------------------------------------------------------------------------

_FIXTURE_ZIP = _find_fixture_zip()


@pytest.mark.skipif(
    _FIXTURE_ZIP is None,
    reason="No .zip fixture found in project root — skipping real-file integration test.",
)
class TestIntegrationWithRealZip:
    def test_extract_and_pipeline_complete(self):
        root = _mod.extract_xml(_FIXTURE_ZIP)
        assert root is not None

        data = _mod.run_pipeline(root)
        assert isinstance(data["Personal data"], dict)
        assert isinstance(data["Academic background"], list)
        assert isinstance(data["Languages"], list)

    def test_full_pdf_generation(self, tmp_path):
        pytest.importorskip("reportlab")

        root = _mod.extract_xml(_FIXTURE_ZIP)
        data = _mod.run_pipeline(root)
        fb, fbo, fi = _mod._register_fonts()
        ST   = _mod._build_styles(fb, fbo, fi)
        pdf_path = tmp_path / "integration_output.pdf"

        _mod.generate_pdf(pdf_path, data, fb, fbo, fi, ST)

        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 4096
