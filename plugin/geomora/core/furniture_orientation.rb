# frozen_string_literal: true

module Geomora
  module Core
    class FurnitureOrientation
      WALL_ANCHORS = %w[wall_north wall_south wall_east wall_west].freeze
      INSET_MM = 600.0

      def self.enabled?(params)
        config = params['building_elements'] || params[:building_elements]
        return false unless config.is_a?(Hash)

        value = config['furniture_wall_align'] || config[:furniture_wall_align]
        value == true || value.to_s == 'true'
      end

      def self.apply(spec, bounds, params)
        orientation = spec[:orientation] || spec[:rotation]
        return spec unless orientation

        if wall_anchor?(orientation)
          position = wall_position(bounds, spec, orientation.to_s)
          return spec.merge(position: position, rotation: wall_rotation(orientation.to_s)) if position
        elsif orientation.is_a?(Numeric) || orientation.to_s.match?(/\A\d+\z/)
          return spec.merge(rotation: orientation.to_i % 360)
        end

        spec
      end

      def self.wall_anchor?(value)
        WALL_ANCHORS.include?(value.to_s)
      end

      def self.wall_rotation(anchor)
        case anchor.to_s
        when 'wall_north' then 0
        when 'wall_south' then 180
        when 'wall_east' then 90
        when 'wall_west' then 270
        else 0
        end
      end

      def self.wall_position(bounds, spec, anchor)
        width = spec[:width].to_f
        depth = spec[:depth].to_f
        inset = INSET_MM
        case anchor.to_s
        when 'wall_north'
          x = bounds[:x_min] + inset
          y = bounds[:y_max] - inset - depth
        when 'wall_south'
          x = bounds[:x_min] + inset
          y = bounds[:y_min] + inset
        when 'wall_east'
          x = bounds[:x_max] - inset - depth
          y = bounds[:y_min] + inset
        when 'wall_west'
          x = bounds[:x_min] + inset
          y = bounds[:y_min] + inset
        else
          return nil
        end
        return nil unless inside_bounds?(x, y, width, depth, bounds, inset)

        [x, y, 0]
      end

      def self.inside_bounds?(x, y, width, depth, bounds, inset)
        x >= bounds[:x_min] + inset &&
          y >= bounds[:y_min] + inset &&
          x + width <= bounds[:x_max] - inset &&
          y + depth <= bounds[:y_max] - inset
      end

      def self.rotated_dimensions(width, depth, rotation_deg)
        angle = rotation_deg.to_i % 180
        angle == 90 ? [depth, width] : [width, depth]
      end

      def self.rotated_corners(x, y, width, depth, rotation_deg, z: 0.0)
        angle = rotation_deg.to_i % 360
        cx = x + (width / 2.0)
        cy = y + (depth / 2.0)
        corners = [
          [x, y],
          [x + width, y],
          [x + width, y + depth],
          [x, y + depth]
        ]
        rad = angle * Math::PI / 180.0
        cos = Math.cos(rad)
        sin = Math.sin(rad)
        corners.map do |px, py|
          dx = px - cx
          dy = py - cy
          [
            cx + (dx * cos) - (dy * sin),
            cy + (dx * sin) + (dy * cos),
            z
          ]
        end
      end
    end
  end
end
