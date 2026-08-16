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
end
