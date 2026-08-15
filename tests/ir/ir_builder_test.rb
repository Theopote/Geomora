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
end
