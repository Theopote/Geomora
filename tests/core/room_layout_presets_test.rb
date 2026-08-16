# frozen_string_literal: true

require_relative '../test_helper'

class RoomLayoutPresetsTest < Minitest::Test
  def test_suggests_layout_for_two_rooms
    params = {
      'partition_count' => 1,
      'storey_count' => 1
    }

    suggestion = Geomora::Core::RoomLayoutPresets.suggest(params)
    assert_includes suggestion, '1:sofa@600,600'
    assert_includes suggestion, '2:'
  end
end
