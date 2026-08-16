# frozen_string_literal: true

require_relative '../test_helper'

class FurniturePlannerTest < Minitest::Test
  def test_places_bed_in_bedroom
    rooms = [
      {
        'id' => 'room_01_01',
        'storey_id' => 'storey_01',
        'semantic' => { 'room_type' => 'bedroom' },
        'geometry' => {
          'polygon' => [
            [0, 0, 0],
            [4000, 0, 0],
            [4000, 3000, 0],
            [0, 3000, 0]
          ]
        }
      }
    ]
    params = {
      'lod_level' => 'lod_300',
      'building_elements' => { 'furniture' => true }
    }

    items = Geomora::Core::FurniturePlanner.plan(rooms: rooms, params: params, storey_index: 0)
    assert_equal 1, items.length
    assert_equal 'bed', items[0]['semantic']['kind']
    assert_equal 'room_01_01', items[0]['room_id']
  end

  def test_skips_furniture_below_lod_300
    rooms = [
      {
        'id' => 'room_01_01',
        'storey_id' => 'storey_01',
        'semantic' => { 'room_type' => 'living' },
        'geometry' => {
          'polygon' => [
            [0, 0, 0],
            [4000, 0, 0],
            [4000, 3000, 0],
            [0, 3000, 0]
          ]
        }
      }
    ]
    params = {
      'lod_level' => 'lod_200',
      'building_elements' => { 'furniture' => true }
    }

    items = Geomora::Core::FurniturePlanner.plan(rooms: rooms, params: params, storey_index: 0)
    assert_equal [], items
  end
end
