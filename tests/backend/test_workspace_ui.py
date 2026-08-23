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
    assert 'id="hypothesis-review"' in html
    assert 'id="hypothesis-list"' in html
    script = (WORKSPACE / "app.js").read_text(encoding="utf-8")
    assert "function renderHypothesisReview()" in script
    assert "function decideHypothesis(index, decision, adjust)" in script
    assert "hypothesis_decisions: Object.assign({}, state.hypothesisDecisions)" in script
    assert "Review all architectural hypotheses before generating" in script


def test_workspace_empty_and_narrow_panel_states_do_not_overflow():
    html = (WORKSPACE / "index.html").read_text(encoding="utf-8")
    styles = (WORKSPACE / "styles.css").read_text(encoding="utf-8")

    assert 'id="viewer-placeholder" class="placeholder empty-viewer"' in html
    assert "[hidden]" in styles
    assert "display: none !important;" in styles
    assert "grid-template-columns: repeat(3, minmax(0, 1fr));" in styles
    assert '.form .checkbox-label input[type="checkbox"]' in styles
    assert "max-height: min(260px, calc(100vh - 150px));" in styles


def test_workspace_uses_compact_tool_density():
    styles = (WORKSPACE / "styles.css").read_text(encoding="utf-8")

    assert "gap: 8px;\n  padding: 8px;" in styles
    assert "min-height: 32px;" in styles
    assert "padding: 7px 8px;" in styles
    assert "margin-bottom: 7px;" in styles
    assert "min-height: 48px;" in styles


def test_analyze_building_uses_reconstruction_pipeline():
    script = (WORKSPACE / "app.js").read_text(encoding="utf-8")
    dialog = (WORKSPACE.parents[1] / "ui" / "workspace_dialog.rb").read_text(encoding="utf-8")

    assert "sketchupCall('reconstruct', JSON.stringify(collectParams()))" in script
    assert "applyReconstruction: applyReconstruction" in script
    assert "Architectural understanding" in script
    assert "add_action_callback('reconstruct')" in dialog
    assert "Perception::ReconstructionClient.reconstruct" in dialog
    assert "renderUnderstandingMarkup" in script
    assert "architecture-storey" in script
    assert "architecture-bay" in script
    assert 'id="show-ai-guides"' in (WORKSPACE / "index.html").read_text(encoding="utf-8")
    assert 'id="uncertainty-review"' in (WORKSPACE / "index.html").read_text(encoding="utf-8")
    assert "function selectUncertainty(index)" in script
    assert "function decideUncertainty(decision)" in script
    assert "data-tree-uncertainty" in script
    assert "uncertainty_decisions: state.uncertaintyDecisions" in script
    assert 'id="opening-evidence"' in (WORKSPACE / "index.html").read_text(encoding="utf-8")
    assert "function renderOpeningEvidence()" in script
    assert "setModelSelection: setModelSelection" in script
    assert "sketchupCall('select_model_entity'" in script
def test_workspace_has_safe_ai_settings_center():
    html = (WORKSPACE / "index.html").read_text(encoding="utf-8")
    script = (WORKSPACE / "app.js").read_text(encoding="utf-8")
    dialog = (WORKSPACE.parent / "workspace_dialog.rb").read_text(encoding="utf-8")

    assert 'id="btn-settings"' in html
    assert 'id="settings-panel"' in html
    assert 'name="routing_mode"' in html
    assert 'name="vlm_provider"' in html
    assert 'name="vlm_api_key"' in html
    assert 'value="openai_compatible"' in html
    assert 'name="vlm_base_url"' in html
    assert 'name="api_key"' not in html
    assert "setSettings: setSettings" in script
    assert "ai_settings: Object.assign({}, state.settings)" in script
    assert "add_action_callback('save_settings')" in dialog
    assert "Continue with this one upload?" in script
    assert "cloud_upload_authorized: state.cloudUploadAuthorized" in script
    assert "!state.settings.cloud_upload_confirm" in script
    assert 'id="ai-evidence-review"' in html
    assert "function renderEvidenceReview()" in script
    assert "evidence_review: state.evidenceReview" in script
    assert "Review the conflicting local and cloud AI evidence" in script
