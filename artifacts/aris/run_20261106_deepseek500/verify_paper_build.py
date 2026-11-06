"""Check the final PDF, citations and embedded fonts after a clean build."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from pypdf import PdfReader


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    tex = (args.build / "paper.tex").read_text(encoding="utf8")
    log = (args.build / "paper.log").read_text(encoding="utf8", errors="replace")
    path = args.build / "paper.pdf"
    pdf = PdfReader(path)
    text = "\n".join(page.extract_text() for page in pdf.pages)
    assert pdf.pages and "??" not in text and "[?]" not in text and "[??]" not in text
    assert "Overfull" not in log
    assert "Interim DeepSeek" not in tex and "Frozen DeepSeek Results" in tex
    cites = {key for group in re.findall(r"\\cite\{([^}]+)\}", tex) for key in group.split(",")}
    bib = set(re.findall(r"\\bibitem\{([^}]+)\}", tex))
    assert cites == bib and len(bib) == 11
    assert set(re.findall(r"\\ref\{([^}]+)\}", tex)) <= set(re.findall(r"\\label\{([^}]+)\}", tex))
    fonts = {}

    def inspect(resources):
        resources = resources.get_object()
        for item in resources.get("/Font", {}).values():
            font = item.get_object()
            if "/DescendantFonts" in font:
                font = font["/DescendantFonts"][0].get_object()
            descriptor = font.get("/FontDescriptor")
            embedded = bool(descriptor and any(k in descriptor.get_object() for k in ("/FontFile", "/FontFile2", "/FontFile3")))
            fonts[str(font.get("/BaseFont"))] = embedded
        for item in resources.get("/XObject", {}).values():
            obj = item.get_object()
            if "/Resources" in obj:
                inspect(obj["/Resources"])

    for page in pdf.pages:
        inspect(page["/Resources"])
    assert fonts and all(fonts.values())
    output = {
        "pages": len(pdf.pages), "paper_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "source_sha256": hashlib.sha256((args.build / "paper.tex").read_bytes()).hexdigest(),
        "embedded_fonts": fonts, "bibliography_entries": len(bib), "unresolved_references": 0,
        "overfull_boxes": 0, "underfull_warnings": log.count("Underfull"),
    }
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf8")
    print(json.dumps(output))


if __name__ == "__main__":
    main()
