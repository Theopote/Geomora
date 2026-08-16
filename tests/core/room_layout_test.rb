# frozen_string_literal: true

require_relative '../test_helper'

class RoomLayoutTest < Minitest::Test
  def test_parses_custom_room_layout
    params = { 'room_furniture_layouts' => '1:sofa@600,600|desk@1800,800' }
    items = Geomora::Core::RoomLayout.items_for_room(
      room_number: 1,
      room_id: 'room_01_01',
      params: params,
      storey_index: 0
    )

    assert_equal 2, items.length
    assert_equal 'sofa', items[0][:kind]
    assert_equal [600.0, 600.0, 0], items[0][:position]
  end

  def test_parses_storey_scoped_layout
    params = { 'room_furniture_layouts' => 's2:1:desk@800,800' }
    ground = Geomora::Core::RoomLayout.items_for_room(
      room_number: 1,
      room_id: 'room_01_01',
      params: params,
      storey_index: 0
    )
    upper = Geomora::Core::RoomLayout.items_for_room(
      room_number: 1,
      room_id: 'room_02_01',
      params: params,
      storey_index: 1
    )

    assert_equal [], ground
    assert_equal 'desk', upper.first[:kind]
  end

  def test_parses_rotation_suffix
    params = { 'room_furniture_layouts' => '1:sofa@600,600@90' }
    items = Geomora::Core::RoomLayout.items_for_room(
      room_number: 1,
      room_id: 'room_01_01',
      params: params,
      storey_index: 0
    )

    assert_equal 90, items.first[:rotation]
  end

  def test_serializes_layout_item
    serialized = Geomora::Core::RoomLayout.serialize_item(
      kind: 'sofa',
      position: [600, 600, 0],
      width: 2000,
      depth: 900,
      height: 800,
      rotation: 90
    )
    assert_equal 'sofa@600,600@90', serialized
  end
end
