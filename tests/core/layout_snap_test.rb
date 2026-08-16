# frozen_string_literal: true

require_relative '../test_helper'

class LayoutSnapTest < Minitest::Test
  def test_snaps_to_grid
    x, y = Geomora::Core::LayoutSnap.snap_position(
      623, 417,
      { x_min: 0, x_max: 4000, y_min: 0, y_max: 3000 },
      width: 2000,
      depth: 900,
      grid_mm: 100,
      wall_magnet: false
    )
    assert_in_delta 600, x, 0.1
    assert_in_delta 400, y, 0.1
  end

  def test_snaps_to_west_wall
    x, y = Geomora::Core::LayoutSnap.snap_position(
      620, 1200,
      { x_min: 0, x_max: 4000, y_min: 0, y_max: 3000 },
      width: 2000,
      depth: 900,
      grid_mm: 100,
      wall_magnet: true,
      magnet_mm: 80
    )
    assert_in_delta 600, x, 0.1
  end
end
