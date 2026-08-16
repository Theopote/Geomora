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
end
