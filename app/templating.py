from pathlib import Path

from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader

templates = Jinja2Templates(
    env=Environment(
        loader=FileSystemLoader(str(Path(__file__).parent / "templates")),
        autoescape=True,
    ),
)
templates.env.filters["money"] = lambda v: f"{v:.2f}"
templates.env.filters["money_grouped"] = lambda v: f"{v:,.2f}"
templates.env.filters["grouped"] = lambda v: f"{v:,}"
