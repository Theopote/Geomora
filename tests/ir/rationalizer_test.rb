# frozen_string_literal: true

require_relative '../test_helper'

class RationalizerTest < Minitest::Test
  def base_params
    {
      'wall_length' => 10_000,
      'wall_height' => 3300,
      'wall_thickness' => 240,
      'windows' => [
        { 'offset' => 480, 'width' => 1520, 'height' => 1480, 'sill_height' => 910 },
        { 'offset' => 2480, 'width' => 1490, 'height' => 1510, 'sill_height' => 890 },
        { 'offset' => 4520, 'width' => 1510, 'height' => 1490, 'sill_height' => 905 },
        { 'offset' => 6510, 'width' => 1505, 'height' => 1505, 'sill_height' => 900 }
      ],
      'door' => { 'offset' => 8500, 'width' => 910, 'height' => 2080 }
    }
  end

  def test_rationalize_equalizes_window_dimensions
    result = Geomora::Core::Rationalizer.rationalize(base_params)
    windows = result['windows']

    assert_equal 4, windows.length
    widths = windows.map { |win| win['width'] }
    heights = windows.map { |win| win['height'] }
    sills = windows.map { |win| win['sill_height'] }

    assert_equal [1500.0], widths.uniq
    assert_equal [1500.0], heights.uniq
    assert_equal [900.0], sills.uniq
  end

  def test_rationalize_layouts_equal_spacing
    result = Geomora::Core::Rationalizer.rationalize(base_params)
    windows = result['windows'].sort_by { |win| win['offset'] }
    gaps = []

    gaps << windows.first['offset'] - 50.0
    (0...(windows.length - 1)).each do |index|
      current_end = windows[index]['offset'] + windows[index]['width']
      gaps << windows[index + 1]['offset'] - current_end
    end
    door_start = base_params['door']['offset']
    gaps << door_start - 50.0 - (windows.last['offset'] + windows.last['width'])

    assert gaps.all? { |gap| (gap - gaps.first).abs <= 50.0 }
  end

  def test_rationalize_builds_constraint_metadata
    result = Geomora::Core::Rationalizer.rationalize(base_params)
    applied = result.dig('rationalization', 'constraints_applied')

    assert_includes applied, 'equal_width'
    assert_includes applied, 'equal_spacing'
    assert_includes applied, 'symmetry'
  end

  def test_rationalize_produces_valid_ir
    params = base_params
    result = Geomora::Core::Rationalizer.rationalize(params)
    merged = params.merge(result)
    ir = Geomora::Core::IRBuilder.build_manual_facade(merged)
    doc = Geomora::IR::Parser.parse(ir)

    assert Geomora::IR::Validator.validate(doc)
    assert_operator ir['constraints'].length, :>=, 4
  end
end
