# frozen_string_literal: true

require_relative '../test_helper'

class FixtureCatalogDiffTest < Minitest::Test
  def setup
    Geomora::Core::FixtureCatalog.clear_cache!
  end

  def test_diff_reports_no_changes_when_cached_matches_disk
    params = { 'building_elements' => { 'fixture_catalog' => true } }
    Geomora::Core::FixtureCatalog.load_catalog(params)
    diff = Geomora::Core::FixtureCatalog.diff(params)
    assert_equal 'No catalog changes', diff['summary']
  end
end
