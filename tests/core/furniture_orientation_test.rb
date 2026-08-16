# frozen_string_literal: true

require_relative '../test_helper'

class FurnitureOrientationTest < Minitest::Test
  def test_wall_north_position
    bounds = { x_min: 0, x_max: 4000, y_min: 0, y_max: 3000 }
    spec = { width: 2000, depth: 900, height: 800, orientation: 'wall_north' }
    result = Geomora::Core::FurnitureOrientation.apply(spec, bounds, {})
    assert result[:position]
    assert_in_delta 1500, result[:position][1], 1.0
  end

  def test_rotated_corners_swap_axes_at_90
    corners = Geomora::Core::FurnitureOrientation.rotated_corners(0, 0, 2000, 1000, 90)
    xs = corners.map { |point| point[0] }
    ys = corners.map { |point| point[1] }
    assert_in_delta 1000, xs.max - xs.min, 1.0
    assert_in_delta 2000, ys.max - ys.min, 1.0
  end
end
