import re
import typing
from pathlib import Path

import bibtexparser
from bibtexparser.bparser import BibTexParser

from academic import cli, import_bibtex
from academic.generate_markdown import GenerateMarkdown

bibtex_dir = Path(__file__).parent / "data"


def test_bibtex_import():
    cli.parse_args(["import", "--dry-run", "tests/data/article.bib", "content/publication/"])


def _process_bibtex(file, expected_count=1) -> "typing.List[GenerateMarkdown]":
    """
    Parse a BibTeX .bib file and return the parsed metadata
    :param file: The .bib file to parse
    :param expected_count: The expected number of entries inside the .bib
    :return: The parsed metadata as a list of EditableFM
    """
    parser = BibTexParser(common_strings=True)
    parser.customization = import_bibtex.convert_to_unicode
    parser.ignore_nonstandard_types = False
    with Path(bibtex_dir, file).open("r", encoding="utf-8") as bibtex_file:
        bib_database = bibtexparser.load(bibtex_file, parser=parser)
        results = []
        for entry in bib_database.entries:
            results.append(import_bibtex.parse_bibtex_entry(entry, dry_run=True))
        assert len(results) == expected_count
        return results


def _test_publication_type(metadata: GenerateMarkdown, expected_type: str):
    """
    Check that the publication_types field of the parsed metadata is set to the expected type.
    """
    assert metadata.yaml["publication_types"] == [expected_type]


def test_bibtex_types():
    """
    This test uses the import_bibtex functions to parse a .bib file and checks that the
    resulting metadata has the correct publication type set.
    """
    _test_publication_type(_process_bibtex("article.bib")[0], "article-journal")
    for metadata in _process_bibtex("report.bib", expected_count=2):
        _test_publication_type(metadata, "report")
    for metadata in _process_bibtex("thesis.bib", expected_count=3):
        _test_publication_type(metadata, "thesis")
    for metadata in _process_bibtex("book.bib", expected_count=2):
        _test_publication_type(metadata, "book")


def test_bibtex_authors_and_tags_cleanup():
    """
    Hyphens in author names should be removed and semicolon-separated keywords
    should be split into multiple tags.
    """
    entry = {
        "ID": "Wang2025Design",
        "ENTRYTYPE": "article",
        "title": "Design of event-triggered adaptive finite-time controller",
        "journal": "International Journal of Control",
        "shortjournal": "Int. J. Control",
        "date": "2025-10-03",
        "author": "Wang, Dong-Mei and Han, Yu-Qun and Lu, Li-Ting and Zhu, Shan-Liang",
        "keywords": "BARRIER LYAPUNOV FUNCTIONS; TRACKING CONTROL; FEEDBACK CONTROL; STABILIZATION",
        "doi": "10.1080/00207179.2025.2461591",
    }
    metadata = import_bibtex.parse_bibtex_entry(entry, dry_run=True)

    assert metadata.yaml["authors"] == ["Dongmei Wang", "Yuqun Han", "Liting Lu", "Shanliang Zhu"]
    assert metadata.yaml["author_notes"] == ["", "", "", ""]
    assert len(metadata.yaml["author_notes"]) == len(metadata.yaml["authors"])
    assert metadata.yaml["publishDate"] == metadata.yaml["date"]
    assert metadata.yaml["publication"] == "International Journal of Control"
    assert metadata.yaml["publication_short"] == "Int. J. Control"
    assert metadata.yaml["tags"] == ["Barrier Lyapunov Functions", "Tracking Control", "Feedback Control", "Stabilization"]
    assert metadata.yaml["hugoblox"]["ids"]["doi"] == "10.1080/00207179.2025.2461591"
    assert "doi" not in metadata.yaml
    assert all("-" not in author for author in metadata.yaml["authors"])
    assert all(";" not in tag for tag in metadata.yaml["tags"])


def test_publication_template_body_is_empty(tmp_path):
    """
    Imported publication markdown should not include the default placeholder body text.
    """
    parser = BibTexParser(common_strings=True)
    parser.customization = import_bibtex.convert_to_unicode
    parser.ignore_nonstandard_types = False

    with Path(bibtex_dir, "article.bib").open("r", encoding="utf-8") as bibtex_file:
        entry = bibtexparser.load(bibtex_file, parser=parser).entries[0]

    import_bibtex.parse_bibtex_entry(entry, pub_dir=tmp_path, dry_run=False, overwrite=True)
    output_path = Path(tmp_path, import_bibtex.slugify(entry["ID"]), "index.md")
    output_text = output_path.read_text(encoding="utf-8")

    assert "Add the **full text** or **supplementary notes** for the publication here using Markdown formatting." not in output_text
    assert "\nlinks:\n  # - type: pdf\n  #   url: \"\"\n" in output_text
    assert "url_pdf:" not in output_text
    assert "url_code:" not in output_text
    assert '\nslides: ""\n' in output_text


def test_abstract_is_single_line_in_output(tmp_path):
    """
    Long abstract text should remain on a single YAML line.
    """
    entry = {
        "ID": "LongAbstract2025",
        "ENTRYTYPE": "article",
        "title": "Long abstract formatting test",
        "journal": "Test Journal",
        "date": "2025-01-01",
        "author": "Wang, Dong-Mei",
        "abstract": (
            "In this article, the problem of event-triggered adaptive finite-time tracking control is investigated "
            "for full-state constrained stochastic nonlinear systems with unknown control directions. In the "
            "backstepping, multi-dimensional Taylor networks are employed to estimate unknown nonlinearities."
        ),
    }

    import_bibtex.parse_bibtex_entry(entry, pub_dir=tmp_path, dry_run=False, overwrite=True)
    output_path = Path(tmp_path, import_bibtex.slugify(entry["ID"]), "index.md")
    output_text = output_path.read_text(encoding="utf-8")

    assert re.search(r"\nabstract: .+\n\n# Summary", output_text)
    assert not re.search(r"\nabstract: .+\n  ", output_text)


def test_title_is_single_line_in_output(tmp_path):
    """
    Long title text should remain on a single YAML line.
    """
    entry = {
        "ID": "LongTitle2025",
        "ENTRYTYPE": "article",
        "title": (
            "Design of event-triggered adaptive finite-time controller for full-state constrained stochastic "
            "nonlinear systems with unknown control directions"
        ),
        "journal": "Test Journal",
        "date": "2025-01-01",
        "author": "Wang, Dong-Mei",
    }

    import_bibtex.parse_bibtex_entry(entry, pub_dir=tmp_path, dry_run=False, overwrite=True)
    output_path = Path(tmp_path, import_bibtex.slugify(entry["ID"]), "index.md")
    output_text = output_path.read_text(encoding="utf-8")

    assert re.search(r"\ntitle: .+\n\n# Authors", output_text)
    assert not re.search(r"\ntitle: .+\n  ", output_text)


def test_doi_is_emitted_in_hugoblox_ids(tmp_path):
    """
    DOI should be output as hugoblox.ids.doi and be double-quoted.
    """
    entry = {
        "ID": "DoiFormat2025",
        "ENTRYTYPE": "article",
        "title": "DOI format test",
        "journal": "Test Journal",
        "date": "2025-01-01",
        "author": "Wang, Dong-Mei",
        "doi": "10.3390/atmos15091043",
    }

    import_bibtex.parse_bibtex_entry(entry, pub_dir=tmp_path, dry_run=False, overwrite=True)
    output_path = Path(tmp_path, import_bibtex.slugify(entry["ID"]), "index.md")
    output_text = output_path.read_text(encoding="utf-8")

    assert "\nhugoblox:\n  ids:\n    doi: \"10.3390/atmos15091043\"\n" in output_text
    assert not re.search(r"(?m)^doi:", output_text)


def test_compact_output_omits_empty_hugoblox(tmp_path):
    """
    Compact output should not contain empty hugoblox ids when DOI is missing.
    """
    parser = BibTexParser(common_strings=True)
    parser.customization = import_bibtex.convert_to_unicode
    parser.ignore_nonstandard_types = False

    with Path(bibtex_dir, "article.bib").open("r", encoding="utf-8") as bibtex_file:
        entry = bibtexparser.load(bibtex_file, parser=parser).entries[0]

    import_bibtex.parse_bibtex_entry(entry, pub_dir=tmp_path, dry_run=False, overwrite=True, compact=True)
    output_path = Path(tmp_path, import_bibtex.slugify(entry["ID"]), "index.md")
    output_text = output_path.read_text(encoding="utf-8")

    assert "hugoblox:" not in output_text


def test_url_is_emitted_in_links_with_type():
    """
    URL fields should be emitted via the `links` list with typed items.
    """
    pdf_entry = {
        "ID": "PdfUrl2025",
        "ENTRYTYPE": "article",
        "title": "PDF URL test",
        "journal": "Test Journal",
        "date": "2025-01-01",
        "author": "Wang, Dong-Mei",
        "url": "https://example.org/paper.pdf",
    }
    pdf_metadata = import_bibtex.parse_bibtex_entry(pdf_entry, dry_run=True)
    assert pdf_metadata.yaml["links"] == [{"type": "pdf", "url": "https://example.org/paper.pdf"}]
    assert "url_pdf" not in pdf_metadata.yaml

    source_entry = {
        "ID": "SourceUrl2025",
        "ENTRYTYPE": "article",
        "title": "Source URL test",
        "journal": "Test Journal",
        "date": "2025-01-01",
        "author": "Wang, Dong-Mei",
        "url": "https://example.org/project",
    }
    source_metadata = import_bibtex.parse_bibtex_entry(source_entry, dry_run=True)
    assert source_metadata.yaml["links"] == [{"type": "source", "url": "https://example.org/project"}]
