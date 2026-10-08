import pytest

from app import ingest


def text_pdf(lines: list[str]) -> bytes:
    """A one-page PDF with a real text layer."""
    ops = "BT /F1 12 Tf 50 750 Td 14 TL " + " ".join(f"({line}) Tj T*" for line in lines) + " ET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(ops)} >>\nstream\n{ops}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    body = "%PDF-1.4\n"
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(body))
        body += f"{i} 0 obj\n{obj}\nendobj\n"
    xref = "xref\n0 6\n0000000000 65535 f \n" + "".join(f"{o:010d} 00000 n \n" for o in offsets)
    trailer = f"trailer\n<< /Root 1 0 R /Size 6 >>\nstartxref\n{len(body)}\n%%EOF\n"
    return (body + xref + trailer).encode("latin-1")


def test_plain_text_stays_text():
    prepared = ingest.from_text("Garlic cures dengue. Forward to all.")
    assert prepared.kind == "text"
    assert prepared.attachments == []


def test_image_becomes_an_attachment():
    prepared = ingest.from_file(b"\x89PNG fake", "Screenshot.PNG")
    assert prepared.kind == "image"
    assert prepared.attachments[0].mime == "image/png"


def test_oversized_image_is_refused():
    with pytest.raises(ingest.IngestError):
        ingest.from_file(b"0" * (ingest.MAX_IMAGE_BYTES + 1), "big.jpg")


def test_unsupported_file_type_is_refused():
    with pytest.raises(ingest.IngestError):
        ingest.from_file(b"MZ", "setup.exe")


def test_pdf_with_text_layer_is_read_as_text():
    lines = [f"Line {i}: the scheme pays 5000 rupees to every registered farmer." for i in range(8)]
    prepared = ingest.from_file(text_pdf(lines), "notice.pdf")
    assert prepared.kind == "pdf"
    assert prepared.attachments == []
    assert "5000 rupees" in prepared.text
    assert "1 pages" in prepared.source


def test_pdf_without_enough_text_goes_to_the_model_as_a_scan():
    prepared = ingest.from_file(text_pdf(["Hi"]), "scan.pdf")
    assert prepared.text == ""
    assert prepared.attachments[0].mime == "application/pdf"


def test_broken_pdf_is_refused():
    with pytest.raises(ingest.IngestError):
        ingest.from_file(b"not a pdf at all", "broken.pdf")


def test_long_text_is_clipped_with_a_note():
    notes: list[str] = []
    clipped = ingest._clip("x" * (ingest.MAX_TEXT_CHARS + 50), notes)
    assert len(clipped) == ingest.MAX_TEXT_CHARS
    assert len(notes) == 1


@pytest.mark.parametrize("url", ["http://127.0.0.1:8000/admin", "http://localhost/", "http://192.168.1.1/", "ftp://example.com/x"])
def test_private_and_non_http_links_are_refused(url):
    with pytest.raises(ingest.IngestError):
        ingest._assert_public(url)


def test_page_text_drops_scripts_and_navigation():
    page = ingest._PageText()
    page.feed(
        "<html><head><title>Fact check</title><script>var x = 'tracking';</script></head>"
        "<body><nav>Home | About</nav><p>The scheme does not exist.</p><footer>Copyright</footer></body></html>"
    )
    assert page.title == "Fact check"
    assert page.text() == "The scheme does not exist."
