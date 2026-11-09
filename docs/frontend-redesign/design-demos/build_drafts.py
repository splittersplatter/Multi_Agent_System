"""Inline demo-data.json and core.js into the draft templates -> dir-1..3.html, thumbs.html."""

from pathlib import Path

HERE = Path(__file__).parent
data = (HERE / "demo-data.json").read_text(encoding="utf-8").replace("</", "<\\/")
core = (HERE / "core.js").read_text(encoding="utf-8")
for src, out in (("src-dir-1.html", "dir-1.html"), ("src-dir-2.html", "dir-2.html"), ("src-dir-3.html", "dir-3.html"), ("src-thumbs.html", "thumbs.html")):
    html = (HERE / src).read_text(encoding="utf-8").replace("/*DATA*/", data).replace("/*CORE*/", core)
    (HERE / out).write_text(html, encoding="utf-8")
    print(out, round(len(html) / 1024), "KB")
