from html.parser import HTMLParser
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[2] / "plugin" / "geomora" / "ui" / "workspace"


class IdCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []

    def handle_starttag(self, _tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"])


def test_workspace_has_unique_ids_and_primary_workflow_controls():
    html = (WORKSPACE / "index.html").read_text(encoding="utf-8")
    parser = IdCollector()
    parser.feed(html)

    assert len(parser.ids) == len(set(parser.ids))
    assert {"btn-pick-image", "btn-rectify", "btn-detect", "btn-validate", "btn-generate"} <= set(parser.ids)
    assert 'class="workflow-steps"' in html
    assert 'class="footer-tools"' in html
    assert html.count('class="icon"') >= 6
    assert 'id="inspector-filter"' in html
    assert 'id="tree-review-only"' in html

    script = (WORKSPACE / "app.js").read_text(encoding="utf-8")
    assert "function enhanceInspector()" in script
    assert "group.open = rawName === 'Windows' || rawName === 'Door'" in script
    assert "data-tree-window" in script
    assert "function escapeHtml(value)" in script


def test_reconstruction_review_remains_accessible():
    html = (WORKSPACE / "index.html").read_text(encoding="utf-8")

    assert 'id="reconstruction-review"' in html
    assert 'id="btn-accept-observed"' in html
    assert 'id="btn-accept-adjusted"' in html
    assert 'id="btn-retry-constraints"' in html


def test_workspace_empty_and_narrow_panel_states_do_not_overflow():
    html = (WORKSPACE / "index.html").read_text(encoding="utf-8")
    styles = (WORKSPACE / "styles.css").read_text(encoding="utf-8")

    assert 'id="viewer-placeholder" class="placeholder empty-viewer"' in html
    assert "[hidden]" in styles
    assert "display: none !important;" in styles
    assert "grid-template-columns: repeat(3, minmax(0, 1fr));" in styles
    assert '.form .checkbox-label input[type="checkbox"]' in styles
    assert "max-height: min(260px, calc(100vh - 150px));" in styles
