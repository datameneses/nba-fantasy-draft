"""Embed data.json into template.html -> index.html (run: python3 build.py)."""
import pathlib
d = pathlib.Path(__file__).parent
data = (d / "data.json").read_text()
(d / "index.html").write_text((d / "template.html").read_text().replace("/*DATA*/", data))
