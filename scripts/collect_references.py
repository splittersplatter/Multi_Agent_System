"""Collect the survey corpus without replacing existing reference files.

Run from the repository root. Outputs are reference data, not simulator state.
Only public publisher, proceedings, author and institutional repositories are used.
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import json
import re
import subprocess
import tempfile
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "References"
MANIFEST = REFS / "manifest.json"
SOURCES = {
    1: ["https://arxiv.org/pdf/1310.6436v1"],
    3: ["https://www.ijcai.org/Proceedings/16/Papers/041.pdf"],
    4: ["https://comsoc-community.org/assets/proceedings/comsoc-2010/Meir.pdf"],
    5: ["https://ifaamas.org/Proceedings/aamas2012/papers/2D_5.pdf"],
    6: ["https://arxiv.org/pdf/1404.4688v2"],
    7: ["https://arxiv.org/pdf/1805.07606"],
    8: ["https://hal.science/hal-01392850/document"],
    9: ["https://www.ifaamas.org/Proceedings/aamas2016/pdfs/p368.pdf"],
    10: ["https://www.ifaamas.org/Proceedings/aamas2018/pdfs/p301.pdf"],
    11: ["https://aamas.csc.liv.ac.uk/Proceedings/aamas2015/aamas/p705.pdf"],
    12: ["https://ojs.aaai.org/index.php/AAAI/article/download/4055/3933"],
    14: ["https://hal.science/hal-04880319/document"],
    15: ["https://ojs.aaai.org/index.php/AAAI/article/download/5556/5412"],
    16: ["https://jair.org/index.php/jair/article/download/12826/26711"],
    17: ["https://www.ifaamas.org/Proceedings/aamas2018/pdfs/p265.pdf"],
    18: ["https://bryanwilder.github.io/files/aaai_election_defense.pdf", "https://arxiv.org/pdf/1809.05521"],
    19: ["https://arxiv.org/pdf/1902.07454"],
    20: ["https://www.ijcai.org/proceedings/2018/0030.pdf"],
    21: ["https://ojs.aaai.org/index.php/AAAI/article/download/16693/16500"],
    22: ["https://www.ijcai.org/proceedings/2022/0079.pdf"],
    23: ["https://arxiv.org/pdf/2308.10845"],
    24: ["https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=10712164"],
    25: ["https://arxiv.org/pdf/2410.12256"],
    26: ["https://arxiv.org/pdf/2510.21200"],
    27: ["https://ide.mit.edu/sites/default/files/publications/2019%20Stewart%20et%20al%20-%20Nature.pdf"],
    28: ["https://arxiv.org/pdf/1309.1131"],
    29: ["https://www.nature.com/articles/s41598-023-50648-6.pdf"],
    30: ["https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0191649&type=printable"],
    31: ["https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0193909&type=printable"],
    32: ["https://arxiv.org/pdf/2512.05982"],
}

PUBLICATIONS = {
    1: "TARK 2013; author preprint", 2: "Studies in Logic 12(3):32-56, 2019; arXiv v2",
    3: "IJCAI 2016, 236-241; proceedings", 4: "AAAI 2010, 823-828; expanded COMSOC 2010 version collected",
    5: "AAMAS 2012; proceedings", 6: "ACM EC 2014; extended arXiv v2 (PDF footer June 2018)",
    7: "arXiv 1805.07606v1, 2018; preprint; later publication not established",
    8: "ECAI 2016, 1423-1431; HAL deposited proceedings with cover",
    9: "AAMAS 2016, 368-375; proceedings", 10: "AAMAS 2018, 301-308; proceedings",
    11: "AAMAS 2015, 705-713; proceedings", 12: "AAAI 2019, 2205-2212; proceedings",
    13: "AAMAS 2020, 132-140; existing browser-print proceedings",
    14: "ECAI 2024, 3541-3548; HAL deposited proceedings with cover",
    15: "AAAI 2020, 1878-1885; proceedings", 16: "JAIR 71:1049-1090, 2021; publisher version",
    17: "AAMAS 2018, 265-273; proceedings", 18: "AAAI 2019; author-hosted full text",
    19: "IJCAI 2019, 201-207; extended arXiv 1902.07454 collected",
    20: "IJCAI 2018, 219-225; proceedings", 21: "AAAI 2021, 5506-5513; proceedings",
    22: "IJCAI 2022, 557-563; proceedings", 23: "2023 proceedings DOI 10.1007/978-3-031-47546-7_32; extended arXiv v1",
    24: "IEEE TCSS 12(1):335-347, February 2025; online 2024; full text blocked",
    25: "AAMAS 2025 extended abstract, 2484-2486; full arXiv version collected",
    26: "arXiv 2510.21200v3, 3 June 2026; preprint; malformed conference template is not venue confirmation",
    27: "Nature 573:117-121, 2019; institutional full text including supplementary information",
    28: "Physical Review Letters 112:158701, 2014; arXiv v2 including supplement",
    29: "Scientific Reports 14:193, 2024; publisher version",
    30: "PLOS ONE 13(2):e0191649, 2018; publisher version; existing browser print preserved",
    31: "PLOS ONE 13(4):e0193909, 2018; publisher version",
    32: "arXiv 2512.05982v1, 2025; PDF/arXiv author claim ICAIS 2025; independent proceedings verification not obtained",
}


def inspect(path: Path) -> dict:
    if not path.read_bytes().startswith(b"%PDF-"):
        raise ValueError("not a PDF")
    info = subprocess.run(["pdfinfo", str(path)], check=True, capture_output=True, text=True).stdout
    pages = int(re.search(r"^Pages:\s+(\d+)", info, re.M)[1])
    extracted = subprocess.run(["pdftotext", "-layout", str(path), "-"], check=True, capture_output=True).stdout.decode("utf-8", "replace")
    return {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size,
            "pages": pages, "extracted_characters": len(extracted),
            "first_page_text": extracted.split("\f")[0][:8000]}


def check_title(details: dict, expected: str) -> float:
    def words(value: str) -> set[str]:
        value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
        return set(re.findall(r"[a-z0-9]+", value))
    wanted = words(expected)
    fraction = len(wanted & words(details["first_page_text"])) / max(1, len(wanted))
    if fraction < 0.75:
        raise ValueError(f"PDF title mismatch ({fraction:.2f} token coverage): {expected}")
    return fraction


def main() -> None:
    previous = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {"papers": []}
    old = {p["id"]: p for p in previous["papers"]}
    text = (ROOT / "docs/election-manipulation-literature-survey.md").read_text()
    records = re.findall(r"^\*\*S(\d+)\.\*\* (.+)$", text, re.M)
    assert len(records) == 32
    existing = list(REFS.glob("*.pdf"))
    original = {
        2: next(p for p in existing if p.name.startswith("How does uncertainty")),
        13: next(p for p in existing if p.name.startswith("Manipulation of Opinion")),
        30: next(p for p in existing if p.name.startswith("Governator")),
    }
    working = Path(tempfile.mkdtemp(prefix="eclipse-paper-audit-"))
    print(f"Text cache: {working}", flush=True)

    def collect(item: tuple[str, str]) -> dict:
        num, citation = int(item[0]), item[1]
        pid = f"S{num}"
        title, stable = re.search(r"\[([^]]+)\]\(([^)]+)\)", citation).groups()
        row = old.get(pid, {"id": pid, "title": title, "citation": citation,
                            "stable_url": stable, "publication_status": "see citation; verify during audit",
                            "attempts": []})
        row["citation"] = citation.split(" **")[0].rstrip(".") + "."
        row["publication_status"] = PUBLICATIONS[num]
        path = ROOT / row["local_path"] if row.get("local_path") else original.get(num)
        if num == 14 and path and inspect(path)["pages"] == 2:
            row["alternate_documents"] = [{"path": row["local_path"], "extent": "ROADEF 2024 two-page abstract; not ECAI full paper"}]
            path = None
            row["local_path"] = None
        if num == 30 and path and path == original[30]:
            row["alternate_documents"] = [{"path": str(path.relative_to(ROOT)), "extent": "existing browser-print PDF; garbled text layer; preserved"}]
            path = None
            row["local_path"] = None
        if num == 19 and path and inspect(path)["pages"] == 7:
            row["alternate_documents"] = [{"path": row["local_path"], "extent": "IJCAI 2019 proceedings; experiments deferred to extended version"}]
            path = None
            row["local_path"] = None
        if num in (16, 25) and path and inspect(path)["pages"] in (37, 3):
            row["alternate_documents"] = [{"path": row["local_path"], "extent": "earlier collected version; retained"}]
            path = None
            row["local_path"] = None
        if not path or not path.exists():
            slug = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode().lower()
            slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")[:95]
            suffix = "-fulltext" if num in (14, 16, 19, 25, 30) else ""
            destination = REFS / f"{pid}-{slug}{suffix}.pdf"
            for url in SOURCES.get(num, []):
                if any(a["url"] == url for a in row["attempts"]):
                    continue  # Do not repeat an unchanged failed access attempt.
                candidate = working / f"{pid}.download"
                run = subprocess.run(["curl", "--fail", "--location", "--silent", "--show-error",
                                      "--connect-timeout", "10", "--max-time", "35", "--max-filesize", "40000000",
                                      "--output", str(candidate), "--write-out", "%{url_effective}", url],
                                     capture_output=True, text=True)
                attempt = {"url": url, "date": "2026-11-07"}
                try:
                    if run.returncode:
                        raise ValueError(run.stderr.strip())
                    check_title(inspect(candidate), title)
                    # Exclusive creation: never clobber an existing reference.
                    with destination.open("xb") as output:
                        output.write(candidate.read_bytes())
                    path = destination
                    row.update(download_url=url, resolved_url=run.stdout,
                               retrieved_on="2026-11-07", origin="downloaded")
                    attempt["result"] = "valid_pdf"
                except (ValueError, subprocess.CalledProcessError, FileExistsError) as exc:
                    attempt["result"] = str(exc)[:400]
                row["attempts"].append(attempt)
                if path:
                    break
        if path and path.exists():
            details = inspect(path)
            if row.get("sha256") and row.get("local_path") and details["sha256"] != row["sha256"]:
                raise ValueError(f"Reference bytes changed since manifest: {pid} ({path}); review version before accepting new hash")
            row["title_token_coverage"] = check_title(details, title)
            first = details.pop("first_page_text")
            version = re.search(r"arXiv:\s*([0-9.]+v\d+)", first)
            row["version"] = "arXiv:" + version[1] if version else PUBLICATIONS[num]
            row.pop("blocker", None)
            subprocess.run(["pdftotext", "-layout", str(path), str(working / f"{pid}.txt")], check=True)
            (working / f"{pid}-first.txt").write_text(first)
            row.update(details, local_path=str(path.relative_to(ROOT)), access_status="pdf_available",
                       checked_on="2026-11-07", origin=row.get("origin", "existing"),
                       version=row["version"])
            row.setdefault("retrieved_on", None)  # Original user files: date unknown.
            row.setdefault("download_url", None)
        else:
            row.update(access_status="blocked", local_path=None,
                       blocker="No verified lawful PDF retrieved; see attempts; author/institutional copy needed.")
            row.update(version=None, retrieved_on=None, download_url=None, sha256=None)
        if num in original:
            row["original_file"] = {"path": str(original[num].relative_to(ROOT)),
                                    "sha256": hashlib.sha256(original[num].read_bytes()).hexdigest()}
        print(f"{pid}: {row['access_status']} {row.get('pages', '')}", flush=True)
        return row

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        papers = list(executor.map(collect, records))
    payload = {"schema_version": 1, "audit_date": "2026-11-07",
               "scope": "Earlier chat corpus S1-S32; existing filenames preserved; primary-source downloads.",
               "papers": papers}
    local_files = []
    for path in sorted(REFS.glob("*.pdf")):
        details = inspect(path)
        details.pop("first_page_text")
        local_files.append({"path": str(path.relative_to(ROOT)), **details})
    payload["local_files"] = local_files
    payload["identical_hash_groups"] = [[f["path"] for f in local_files if f["sha256"] == sha]
                                        for sha in sorted({f["sha256"] for f in local_files})
                                        if sum(f["sha256"] == sha for f in local_files) > 1]
    MANIFEST.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"available": sum(p["access_status"] == "pdf_available" for p in papers),
                      "blocked": [p["id"] for p in papers if p["access_status"] == "blocked"],
                      "text_cache": str(working)}, indent=2))


if __name__ == "__main__":
    main()
