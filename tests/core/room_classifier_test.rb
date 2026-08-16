# frozen_string_literal: true

require_relative '../test_helper'

class RoomClassifierTest < Minitest::Test
  def test_classifies_two_room_layout
    rooms = [
      {
        'id' => 'room_01_01',
        'semantic' => { 'area_mm2' => 10_000_000 },
        'name' => 'Room 1'
      },
      {
        'id' => 'room_01_02',
        'semantic' => { 'area_mm2' => 8_000_000 },
        'name' => 'Room 2'
      }
    ]

    classified = Geomora::Core::RoomClassifier.classify(rooms, params: {}, storey_index: 0)
    assert_equal 'living', classified[0]['semantic']['room_type']
    assert_equal 'study', classified[1]['semantic']['room_type']
  end

  def test_classifies_three_rooms_with_bathroom
    rooms = [
      { 'id' => 'r1', 'semantic' => { 'area_mm2' => 12_000_000 }, 'name' => 'Room 1' },
      { 'id' => 'r2', 'semantic' => { 'area_mm2' => 9_000_000 }, 'name' => 'Room 2' },
      { 'id' => 'r3', 'semantic' => { 'area_mm2' => 3_000_000 }, 'name' => 'Room 3' }
    ]

    classified = Geomora::Core::RoomClassifier.classify(rooms, params: {}, storey_index: 0)
    types = classified.map { |room| room['semantic']['room_type'] }
    assert_includes types, 'living'
    assert_includes types, 'bathroom'
  end
end
