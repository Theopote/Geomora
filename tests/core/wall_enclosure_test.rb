# frozen_string_literal: true

require_relative '../test_helper'

class WallEnclosureTest < Minitest::Test
  def test_perimeter_walls_form_closed_loop
    walls = Geomora::Core::WallEnclosure.perimeter_walls(
      wall_length: 10_000,
      wall_thickness: 240,
      building_depth: 6000,
      storey_id: 'storey_01',
      storey_index: 0,
      wall_height: 3300,
      facade_wall_id: 'wall_01_01'
    )

    assert_equal 4, walls.length
    roles = walls.map { |wall| wall['semantic']['join_role'] }
    assert_equal %w[facade back left right], roles
    assert_equal 'perimeter', walls.first['semantic']['join_group']
  end

  def test_enabled_flag_reads_building_elements
    assert Geomora::Core::WallEnclosure.enabled?(
      'building_elements' => { 'perimeter_walls' => true }
    )
    assert_equal false, Geomora::Core::WallEnclosure.enabled?(
      'building_elements' => { 'perimeter_walls' => false }
    )
  end
end
