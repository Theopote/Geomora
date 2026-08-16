# frozen_string_literal: true

require_relative '../test_helper'

class RoomOverridesTest < Minitest::Test
  def test_overrides_room_type_by_index
    rooms = [
      { 'id' => 'room_01_01', 'name' => 'Room 1', 'semantic' => { 'room_type' => 'living' } },
      { 'id' => 'room_01_02', 'name' => 'Room 2', 'semantic' => { 'room_type' => 'bedroom' } }
    ]
    params = { 'room_type_overrides' => '2:kitchen' }

    result = Geomora::Core::RoomOverrides.apply(rooms, params: params, storey_index: 0)
    assert_equal 'living', result[0]['semantic']['room_type']
    assert_equal 'kitchen', result[1]['semantic']['room_type']
    assert_equal true, result[1]['semantic']['override']
  end
end
