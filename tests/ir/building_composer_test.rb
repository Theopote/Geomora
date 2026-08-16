# frozen_string_literal: true

require_relative '../test_helper'

class BuildingComposerTest < Minitest::Test
  def test_compose_floor_and_roof_by_default_flags
    params = {
      'building_elements' => { 'floor' => true, 'roof' => true },
      'building_depth' => 6000
    }

    elements = Geomora::Core::BuildingComposer.compose(
      params,
      wall_length: 10_000,
      wall_height: 3300,
      wall_thickness: 240,
      storey_id: 'storey_01'
    )

    assert_equal 2, elements.length
    assert_equal 'floor', elements[0]['type']
    assert_equal 'roof', elements[1]['type']
    assert_equal 4, elements[0]['geometry']['polygon'].length
    assert_equal 3300, elements[1]['geometry']['elevation']
  end

  def test_compose_optional_structural_elements
    params = {
      'building_elements' => {
        'columns' => true,
        'beam' => true,
        'stair' => true
      },
      'stair_steps' => 10
    }

    elements = Geomora::Core::BuildingComposer.compose(
      params,
      wall_length: 8000,
      wall_height: 3000,
      wall_thickness: 240,
      storey_id: 'storey_01'
    )

    types = elements.map { |element| element['type'] }
    assert_includes types, 'column'
    assert_includes types, 'beam'
    assert_includes types, 'stair'
    assert_equal 10, elements.find { |e| e['type'] == 'stair' }['geometry']['steps']
  end

  def test_compose_exterior_elements
    params = {
      'building_elements' => {
        'balcony' => true,
        'parapet' => true,
        'cornice' => true
      },
      'windows' => [{ 'offset' => 1200, 'width' => 1800, 'height' => 1500, 'sill_height' => 900 }]
    }

    elements = Geomora::Core::BuildingComposer.compose(
      params,
      wall_length: 10_000,
      wall_height: 3300,
      wall_thickness: 240,
      storey_id: 'storey_01'
    )

    types = elements.map { |element| element['type'] }
    assert_includes types, 'balcony'
    assert_includes types, 'parapet'
    assert_includes types, 'cornice'
    balcony = elements.find { |e| e['type'] == 'balcony' }
    assert_equal 1200, balcony['geometry']['position'][0]
    assert_equal 1800, balcony['geometry']['width']
  end
end
