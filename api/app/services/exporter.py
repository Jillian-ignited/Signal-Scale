from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path

template_dir = Path(__file__).resolve().parents[1] / "templates"
env = Environment(
    loader=FileSystemLoader(str(template_dir)),
    autoescape=select_autoescape()
)

def export_html(data: dict) -> str:
    template = env.get_template("report.html")
    return template.render(data=data)

def export_markdown(data: dict) -> str:
    template = env.get_template("report.md.j2")
    return template.render(data=data)
