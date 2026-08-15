# frozen_string_literal: true

require_relative '../test_helper'

class PatternAnalyzerTest < Minitest::Test
  def rationalized_params
    result = Geomora::Core::Rationalizer.rationalize(
      'wall_length' => 10_000,
      'wall_height' => 3300,
      'windows' => [
        { 'offset' => 480, 'width' => 1520, 'height' => 1480, 'sill_height' => 910 },
        { 'offset' => 2480, 'width' => 1490, 'height' => 1510, 'sill_height' => 890 },
        { 'offset' => 4520, 'width' => 1510, 'height' => 1490, 'sill_height' => 905 },
        { 'offset' => 6510, 'width' => 1505, 'height' => 1505, 'sill_height' => 900 }
      ],
      'door' => { 'offset' => 8500, 'width' => 910, 'height' => 2080 }
    )
    {
      'wall_length' => 10_000,
      'wall_height' => 3300,
      'windows' => result['windows'],
      'door' => result['door'],
      'rationalization' => result['rationalization']
    }
  end

  def test_detects_translation_grid_pattern
    result = Geomora::Core::PatternAnalyzer.analyze(rationalized_params)
    pattern = result['pattern']

    assert_equal 'translation_grid', pattern['type']
    assert_includes pattern['patterns_detected'], 'translation'
    assert_includes pattern['patterns_detected'], 'grid'
    assert_includes pattern['patterns_detected'], 'window_bay'
    assert_equal 'window_bay_1500x1500', pattern['component_id']
    assert_equal 4, pattern['bay_count']
    assert pattern['bay_pitch']
  end

  def test_assigns_shared_component_id_to_windows
    result = Geomora::Core::PatternAnalyzer.analyze(rationalized_params)
    component_ids = result['windows'].map { |win| win['component_id'] }.uniq

    assert_equal ['window_bay_1500x1500'], component_ids
  end

  def test_builds_ir_with_grid_constraint
    analyzed = Geomora::Core::PatternAnalyzer.analyze(rationalized_params)
    merged = rationalized_params.merge(analyzed)
    ir = Geomora::Core::IRBuilder.build_manual_facade(merged)
    doc = Geomora::IR::Parser.parse(ir)

    assert Geomora::IR::Validator.validate(doc)
    grid = ir['constraints'].find { |item| item['type'] == 'grid' }
    refute_nil grid
    assert_equal 4, grid.dig('parameters', 'bay_count')
    assert_equal 1, ir['components'].count { |item| item['type'] == 'window' }
  end
end
