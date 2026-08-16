# frozen_string_literal: true

require_relative '../test_helper'

class RoomLayoutEditorTest < Minitest::Test
  def test_preview_returns_rooms_for_partition_count
    params = {
      'wall_length' => 9000,
      'building_depth' => 6000,
      'partition_count' => 1
    }
    rooms = Geomora::Core::RoomLayoutEditor.preview(params)
    assert_equal 2, rooms.length
    assert rooms.first['items'].any?
  end

  def test_preview_all_storeys_returns_multiple_floors
    params = {
      'wall_length' => 9000,
      'building_depth' => 6000,
      'partition_count' => 1,
      'storey_count' => 2
    }
    storeys = Geomora::Core::RoomLayoutEditor.preview_all_storeys(params)
    assert_equal 2, storeys.length
    assert_equal 'Ground', storeys.first['label']
    assert_equal 'Floor 2', storeys.last['label']
  end
end
