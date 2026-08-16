# frozen_string_literal: true

require_relative '../test_helper'

class FixtureCatalogTest < Minitest::Test
  def test_loads_default_catalog_items
    params = { 'building_elements' => { 'fixture_catalog' => true } }
    items = Geomora::Core::FixtureCatalog.items_for('kitchen', params)
    kinds = items.map { |item| item[:kind] }
    assert_includes kinds, 'island'
  end

  def test_reload_clears_cache
    params = { 'building_elements' => { 'fixture_catalog' => true } }
    first = Geomora::Core::FixtureCatalog.load_catalog(params)
    Geomora::Core::FixtureCatalog.clear_cache!
    second = Geomora::Core::FixtureCatalog.load_catalog(params, force: true)
    assert_equal first['version'], second['version']
  end
end
