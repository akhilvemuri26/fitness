from starlette.requests import Request
from starlette.templating import Jinja2Templates


templates = Jinja2Templates(directory="app/templates")


def _render_base(root_path: str = "") -> str:
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "root_path": root_path,
            "headers": [],
            "query_string": b"",
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
            "scheme": "http",
        }
    )
    template = templates.get_template("base.html")
    return template.render({"request": request, "title": "Template Test"})


def test_base_template_uses_root_relative_stylesheet_href() -> None:
    rendered = _render_base()

    assert 'href="/static/styles.css"' in rendered
    assert "http://testserver/static/styles.css" not in rendered


def test_base_template_preserves_root_path_for_stylesheet_href() -> None:
    rendered = _render_base("/fitness")

    assert 'href="/fitness/static/styles.css"' in rendered
    assert "http://testserver/fitness/static/styles.css" not in rendered
