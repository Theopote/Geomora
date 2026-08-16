# frozen_string_literal: true

require_relative '../test_helper'

class FixtureCatalogPaletteTest < Minitest::Test
  def test_palette_includes_catalog_and_builtin_items
    params = { 'building_elements' => { 'fixture_catalog' => true } }
    palette = Geomora::Core::FixtureCatalog.palette(params)
    kinds = palette.map { |entry| entry[:kind] }
    assert_includes kinds, 'sofa'
    assert_includes kinds, 'island'
  end
end
