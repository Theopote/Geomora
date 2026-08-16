# frozen_string_literal: true

require_relative '../test_helper'

class FurnitureCollisionTest < Minitest::Test
  def test_resolves_overlapping_items
    items = [
      { position: [600, 600, 0], width: 2000, depth: 900 },
      { position: [600, 600, 0], width: 1000, depth: 600 }
    ]
    bounds = { x_min: 0, x_max: 5000, y_min: 0, y_max: 4000 }

    resolved = Geomora::Core::FurnitureCollision.resolve(items, bounds)
    first = resolved[0][:position]
    second = resolved[1][:position]
    refute Geomora::Core::FurnitureCollision.overlaps?(
      first, resolved[0][:width], resolved[0][:depth],
      second, resolved[1][:width], resolved[1][:depth],
      Geomora::Core::FurnitureCollision::GAP_MM
    )
  end
end
