# frozen_string_literal: true

module Geomora
  module Core
    class LayoutSnap
      DEFAULT_GRID_MM = 100.0
      DEFAULT_MAGNET_MM = 80.0

      def self.snap_position(x, y, bounds, width:, depth:, grid_mm: DEFAULT_GRID_MM, wall_magnet: true, magnet_mm: DEFAULT_MAGNET_MM)
        snapped_x = snap_axis(x, grid_mm)
        snapped_y = snap_axis(y, grid_mm)
        if wall_magnet
          wall = snap_to_walls(snapped_x, snapped_y, bounds, width: width, depth: depth, magnet_mm: magnet_mm)
          snapped_x = wall[:x]
          snapped_y = wall[:y]
        end
        [snapped_x, snapped_y]
      end

      def self.snap_axis(value, grid_mm)
        grid = grid_mm.to_f
        return value.to_f if grid <= 0

        (value.to_f / grid).round * grid
      end

      def self.snap_to_walls(x, y, bounds, width:, depth:, magnet_mm:)
        inset = 600.0
        candidates = [
          { x: bounds[:x_min] + inset, y: y, dist: (x - (bounds[:x_min] + inset)).abs },
          { x: bounds[:x_max] - inset - width, y: y, dist: (x - (bounds[:x_max] - inset - width)).abs },
          { x: x, y: bounds[:y_min] + inset, dist: (y - (bounds[:y_min] + inset)).abs },
          { x: x, y: bounds[:y_max] - inset - depth, dist: (y - (bounds[:y_max] - inset - depth)).abs }
        ]
        best = candidates.min_by { |candidate| candidate[:dist] }
        if best[:dist] <= magnet_mm.to_f
          { x: best[:x], y: best[:y] }
        else
          { x: x, y: y }
        end
      end
    end
  end
end
