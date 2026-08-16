# frozen_string_literal: true

require_relative '../test_helper'

class StructuralGridTest < Minitest::Test
  def test_column_positions_cover_span
    positions = Geomora::Core::StructuralGrid.column_positions(
      wall_length: 10_000,
      building_depth: 6000,
      column_size: 400,
      grid_x_spacing: 3000,
      grid_y_spacing: 3000
    )

    assert positions.length > 4
    assert_includes positions, [0, 0]
    assert_includes positions, [9600, 5600]
  end

  def test_grid_column_elements_use_storey_prefix
    elements = Geomora::Core::StructuralGrid.column_elements(
      params: { 'grid_x_spacing' => 5000, 'grid_y_spacing' => 3000 },
      wall_length: 10_000,
      building_depth: 6000,
      column_size: 400,
      wall_height: 3300,
      storey_id: 'storey_01',
      storey_index: 0,
      id_prefix: 'grid_col'
    )

    assert elements.length >= 4
    assert_equal 'column', elements.first['type']
    assert elements.first['semantic']['grid']
  end
end
