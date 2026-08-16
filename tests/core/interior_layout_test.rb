# frozen_string_literal: true

require_relative '../test_helper'

class InteriorLayoutTest < Minitest::Test
  def test_disabled_by_default
    refute Geomora::Core::InteriorLayout.enabled?({})
    refute Geomora::Core::InteriorLayout.enabled?({ 'building_elements' => {} })
  end

  def test_enabled_with_flag
    params = { 'building_elements' => { 'interior_partitions' => true } }
    assert Geomora::Core::InteriorLayout.enabled?(params)
  end

  def test_single_partition_without_perimeter
    params = { 'partition_count' => 1 }
    walls = Geomora::Core::InteriorLayout.partition_walls(
      params: params,
      wall_length: 9000,
      wall_thickness: 240,
      building_depth: 6000,
      storey_id: 'storey_01',
      storey_index: 0,
      wall_height: 3000,
      perimeter_walls: false
    )

    assert_equal 1, walls.length
    assert_equal 'partition_01_01', walls[0]['id']
    assert_equal 4500, walls[0]['geometry']['baseline'][0][0]
    assert_equal true, walls[0]['semantic']['interior']
  end

  def test_multiple_partitions_with_perimeter
    params = { 'partition_count' => 2 }
    walls = Geomora::Core::InteriorLayout.partition_walls(
      params: params,
      wall_length: 9000,
      wall_thickness: 240,
      building_depth: 6000,
      storey_id: 'storey_01',
      storey_index: 0,
      wall_height: 3000,
      perimeter_walls: true
    )

    assert_equal 2, walls.length
    y_start = walls[0]['geometry']['baseline'][0][1]
    y_end = walls[0]['geometry']['baseline'][1][1]
    assert_equal 120, y_start
    assert_equal 2880, y_end
  end
end
