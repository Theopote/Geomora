# frozen_string_literal: true

module Geomora
  module Core
    class FurnitureCollision
      STEP_MM = 200.0
      GAP_MM = 100.0

      def self.enabled?(params)
        config = params['building_elements'] || params[:building_elements]
        return false unless config.is_a?(Hash)

        value = config['furniture_collision'] || config[:furniture_collision]
        value == true || value.to_s == 'true'
      end

      def self.resolve(items, bounds, gap: GAP_MM)
        placed = []
        items.map do |item|
          position = item[:position] || [0, 0, 0]
          resolved = find_position(
            position,
            item[:width].to_f,
            item[:depth].to_f,
            placed,
            bounds,
            gap: gap
          )
          next nil unless resolved

          resolved_item = item.merge(position: resolved)
          placed << resolved_item
          resolved_item
        end.compact
      end

      def self.find_position(start, width, depth, placed, bounds, gap:)
        inset = 600.0
        candidates = candidate_positions(start, bounds, width, depth, inset)
        candidates.each do |position|
          next unless inside_bounds?(position, width, depth, bounds, inset)
          next if overlaps_any?(position, width, depth, placed, gap)

          return position
        end
        nil
      end

      def self.candidate_positions(start, bounds, width, depth, inset)
        x0 = start[0].to_f
        y0 = start[1].to_f
        shifts = [0, STEP_MM, -STEP_MM, STEP_MM * 2, -STEP_MM * 2, STEP_MM * 3]
        positions = [[x0, y0, 0]]
        shifts.each do |dx|
          shifts.each do |dy|
            next if dx.zero? && dy.zero?

            positions << [x0 + dx, y0 + dy, 0]
          end
        end
        positions
      end

      def self.inside_bounds?(position, width, depth, bounds, inset)
        x = position[0].to_f
        y = position[1].to_f
        x >= bounds[:x_min] + inset &&
          y >= bounds[:y_min] + inset &&
          x + width <= bounds[:x_max] - inset &&
          y + depth <= bounds[:y_max] - inset
      end

      def self.overlaps_any?(position, width, depth, placed, gap)
        placed.any? do |other|
          overlaps?(
            position, width, depth,
            other[:position], other[:width].to_f, other[:depth].to_f,
            gap
          )
        end
      end

      def self.overlaps?(a_pos, a_w, a_d, b_pos, b_w, b_d, gap)
        a_left = a_pos[0].to_f - gap
        a_right = a_pos[0].to_f + a_w + gap
        a_bottom = a_pos[1].to_f - gap
        a_top = a_pos[1].to_f + a_d + gap
        b_left = b_pos[0].to_f
        b_right = b_pos[0].to_f + b_w
        b_bottom = b_pos[1].to_f
        b_top = b_pos[1].to_f + b_d
        a_left < b_right && b_left < a_right && a_bottom < b_top && b_bottom < a_top
      end
    end
  end
end
