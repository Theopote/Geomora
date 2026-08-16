# frozen_string_literal: true

require_relative '../test_helper'

class RoomPlannerTest < Minitest::Test
  def test_requires_partitions_and_room_zones_flag
    params = {
      'building_elements' => { 'interior_partitions' => true, 'room_zones' => true },
      'partition_count' => 1
    }

    rooms = Geomora::Core::RoomPlanner.plan(
      params: params,
      wall_length: 9000,
      building_depth: 6000,
      storey_id: 'storey_01',
      storey_index: 0,
      perimeter_walls: true
    )

    assert_equal 2, rooms.length
    assert_equal 'Room 1', rooms[0]['name']
    assert_equal 'Room 2', rooms[1]['name']
    assert rooms[0]['semantic']['area_mm2'].positive?
  end

  def test_disabled_without_room_zones
    params = { 'building_elements' => { 'interior_partitions' => true } }
    rooms = Geomora::Core::RoomPlanner.plan(
      params: params,
      wall_length: 9000,
      building_depth: 6000,
      storey_id: 'storey_01',
      storey_index: 0,
      perimeter_walls: false
    )

    assert_equal [], rooms
  end
end
