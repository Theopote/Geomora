# frozen_string_literal: true

require_relative '../test_helper'

class IRBuilderTest < Minitest::Test
  def test_builds_valid_phase0_equivalent
    params = {
      'project_name' => 'Phase 0 Test',
      'wall_length' => 10_000,
      'wall_height' => 3300,
      'wall_thickness' => 240,
      'windows' => [
        { 'offset' => 500, 'width' => 1500, 'height' => 1500, 'sill_height' => 900 },
        { 'offset' => 2500, 'width' => 1500, 'height' => 1500, 'sill_height' => 900 },
        { 'offset' => 4500, 'width' => 1500, 'height' => 1500, 'sill_height' => 900 },
        { 'offset' => 6500, 'width' => 1500, 'height' => 1500, 'sill_height' => 900 }
      ],
      'door' => { 'offset' => 8500, 'width' => 900, 'height' => 2100 }
    }

    ir = Geomora::Core::IRBuilder.build_manual_facade(params)
    doc = Geomora::IR::Parser.parse(ir)

    assert Geomora::IR::Validator.validate(doc)
    assert_equal 4, ir['openings'].count { |o| o['type'] == 'window' }
    assert_equal 1, ir['openings'].count { |o| o['type'] == 'door' }
  end

  def test_builds_floor_and_roof_when_enabled
    params = {
      'project_name' => 'Phase 7 Test',
      'wall_length' => 10_000,
      'wall_height' => 3300,
      'wall_thickness' => 240,
      'building_depth' => 6000,
      'building_elements' => { 'floor' => true, 'roof' => true },
      'windows' => [{ 'offset' => 500, 'width' => 1500, 'height' => 1500, 'sill_height' => 900 }],
      'door' => { 'offset' => 0, 'width' => 0, 'height' => 0 }
    }

    ir = Geomora::Core::IRBuilder.build_manual_facade(params)
    doc = Geomora::IR::Parser.parse(ir)

    assert Geomora::IR::Validator.validate(doc)
    elements = ir['buildings'][0]['storeys'][0]['elements']
    types = elements.map { |element| element['type'] }
    assert_includes types, 'wall'
    assert_includes types, 'floor'
    assert_includes types, 'roof'
  end

  def test_builds_multi_storey_stack
    params = {
      'project_name' => 'Multi Storey',
      'wall_length' => 10_000,
      'wall_height' => 3300,
      'wall_thickness' => 240,
      'storey_count' => 2,
      'storey_height' => 3000,
      'repeat_openings' => true,
      'windows' => [
        { 'offset' => 500, 'width' => 1500, 'height' => 1500, 'sill_height' => 900 }
      ],
      'door' => { 'offset' => 8500, 'width' => 900, 'height' => 2100 }
    }

    ir = Geomora::Core::IRBuilder.build_manual_facade(params)
    doc = Geomora::IR::Parser.parse(ir)

    assert Geomora::IR::Validator.validate(doc)
    assert_equal 2, ir['buildings'][0]['storeys'].length
    assert_equal 0, ir['buildings'][0]['storeys'][0]['elevation']
    assert_equal 3000, ir['buildings'][0]['storeys'][1]['elevation']
    assert_equal 2, ir['openings'].count { |opening| opening['type'] == 'window' }
    assert_equal 1, ir['openings'].count { |opening| opening['type'] == 'door' }
  end

  def test_builds_perimeter_walls_when_enabled
    params = {
      'project_name' => 'Perimeter',
      'wall_length' => 8000,
      'wall_height' => 3000,
      'wall_thickness' => 240,
      'building_depth' => 6000,
      'building_elements' => { 'perimeter_walls' => true },
      'windows' => [],
      'door' => { 'offset' => 0, 'width' => 0, 'height' => 0 }
    }

    ir = Geomora::Core::IRBuilder.build_manual_facade(params)
    walls = ir['buildings'][0]['storeys'][0]['elements'].select { |e| e['type'] == 'wall' }

    assert_equal 4, walls.length
    assert_equal 'perimeter', walls.first['semantic']['join_group']
  end

  def test_lod_100_excludes_openings
    params = {
      'project_name' => 'LOD 100',
      'wall_length' => 8000,
      'wall_height' => 3000,
      'wall_thickness' => 240,
      'lod_level' => 'lod_100',
      'windows' => [{ 'offset' => 500, 'width' => 1500, 'height' => 1500, 'sill_height' => 900 }],
      'door' => { 'offset' => 0, 'width' => 900, 'height' => 2100 }
    }

    ir = Geomora::Core::IRBuilder.build_manual_facade(params)
    assert_equal 'lod_100', ir['project']['lod_level']
    assert_equal [], ir['openings']
  end

  def test_lod_300_adds_trim_when_windows_present
    params = {
      'project_name' => 'LOD 300',
      'wall_length' => 8000,
      'wall_height' => 3000,
      'wall_thickness' => 240,
      'lod_level' => 'lod_300',
      'building_elements' => { 'roof' => true, 'balcony' => true },
      'windows' => [{ 'offset' => 500, 'width' => 1500, 'height' => 1500, 'sill_height' => 900 }],
      'door' => { 'offset' => 0, 'width' => 0, 'height' => 0 }
    }

    ir = Geomora::Core::IRBuilder.build_manual_facade(params)
    doc = Geomora::IR::Parser.parse(ir)

    assert Geomora::IR::Validator.validate(doc)
    types = ir['buildings'][0]['storeys'][0]['elements'].map { |element| element['type'] }
    assert_includes types, 'trim'
    assert_includes types, 'eaves'
  end

  def test_independent_storey_windows
    params = {
      'project_name' => 'Per-floor windows',
      'wall_length' => 10_000,
      'wall_height' => 3300,
      'wall_thickness' => 240,
      'storey_count' => 2,
      'repeat_openings' => false,
      'storey_windows' => [
        [{ 'offset' => 500, 'width' => 1500, 'height' => 1500, 'sill_height' => 900 }],
        [{ 'offset' => 2500, 'width' => 1200, 'height' => 1200, 'sill_height' => 1000 }]
      ],
      'windows' => [{ 'offset' => 500, 'width' => 1500, 'height' => 1500, 'sill_height' => 900 }],
      'door' => { 'offset' => 0, 'width' => 0, 'height' => 0 }
    }

    ir = Geomora::Core::IRBuilder.build_manual_facade(params)
    doc = Geomora::IR::Parser.parse(ir)

    assert Geomora::IR::Validator.validate(doc)
    offsets = ir['openings'].select { |o| o['type'] == 'window' }.map { |o| o.dig('geometry', 'offset') }
    assert_includes offsets, 500.0
    assert_includes offsets, 2500.0
  end

  def test_builds_interior_partitions_when_enabled
    params = {
      'project_name' => 'Interior',
      'wall_length' => 9000,
      'wall_height' => 3000,
      'wall_thickness' => 240,
      'building_depth' => 6000,
      'partition_count' => 2,
      'building_elements' => { 'interior_partitions' => true, 'perimeter_walls' => true },
      'windows' => [],
      'door' => { 'offset' => 0, 'width' => 0, 'height' => 0 }
    }

    ir = Geomora::Core::IRBuilder.build_manual_facade(params)
    doc = Geomora::IR::Parser.parse(ir)

    assert Geomora::IR::Validator.validate(doc)
    walls = ir['buildings'][0]['storeys'][0]['elements'].select { |e| e['type'] == 'wall' }
    partitions = walls.select { |wall| wall['semantic']['interior'] }
    assert_equal 6, walls.length
    assert_equal 2, partitions.length
  end

  def test_builds_rooms_and_partition_doors
    params = {
      'project_name' => 'Rooms',
      'wall_length' => 9000,
      'wall_height' => 3000,
      'wall_thickness' => 240,
      'building_depth' => 6000,
      'partition_count' => 1,
      'building_elements' => {
        'interior_partitions' => true,
        'partition_doors' => true,
        'room_zones' => true
      },
      'windows' => [],
      'door' => { 'offset' => 0, 'width' => 0, 'height' => 0 }
    }

    ir = Geomora::Core::IRBuilder.build_manual_facade(params)
    doc = Geomora::IR::Parser.parse(ir)

    assert Geomora::IR::Validator.validate(doc)
    assert_equal 2, ir['rooms'].length
    assert_equal 1, ir['openings'].count { |opening| opening['id'].start_with?('partition_door') }
  end

  def test_classifies_rooms_and_places_furniture
    params = {
      'project_name' => 'Phase 13',
      'wall_length' => 9000,
      'wall_height' => 3000,
      'wall_thickness' => 240,
      'building_depth' => 6000,
      'lod_level' => 'lod_300',
      'partition_count' => 1,
      'building_elements' => {
        'interior_partitions' => true,
        'room_zones' => true,
        'room_types' => true,
        'furniture' => true
      },
      'windows' => [],
      'door' => { 'offset' => 0, 'width' => 0, 'height' => 0 }
    }

    ir = Geomora::Core::IRBuilder.build_manual_facade(params)
    doc = Geomora::IR::Parser.parse(ir)

    assert Geomora::IR::Validator.validate(doc)
    assert_equal 'living', ir['rooms'][0]['semantic']['room_type']
    assert_equal 2, ir['furniture'].length
  end
end
