# frozen_string_literal: true

module Geomora
  module Core
    class RoomPlanner
      ZONE_NAMES = %w[front_left front_centre front_right rear_left rear_centre rear_right].freeze

      def self.enabled?(params)
        config = params['building_elements'] || params[:building_elements]
        return false unless config.is_a?(Hash)

        value = config['room_zones'] || config[:room_zones]
        value == true || value.to_s == 'true'
      end

      def self.plan(
        params:,
        wall_length:,
        building_depth:,
        storey_id:,
        storey_index:,
        perimeter_walls: false
      )
        return [] unless enabled?(params)
        return [] unless InteriorLayout.enabled?(params)

        y_range = InteriorLayout.interior_y_range(building_depth, partition_thickness(params), perimeter_walls)
        x_bounds = partition_x_bounds(params, wall_length)
        suffix = format('%02d', storey_index + 1)

        bounds = []
        (0...(x_bounds.length - 1)).each do |index|
          bounds << {
            x_min: x_bounds[index],
            x_max: x_bounds[index + 1],
            y_min: y_range[:start],
            y_max: y_range[:end]
          }
        end

        bounds.map.with_index do |bound, index|
          {
            'id' => format('room_%s_%02d', suffix, index + 1),
            'storey_id' => storey_id,
            'name' => room_name(index, bounds.length),
            'geometry' => {
              'polygon' => room_polygon(bound),
              'elevation' => 0
            },
            'semantic' => {
              'zone' => zone_name(index, bounds.length),
              'room_type' => 'generic',
              'area_mm2' => room_area(bound)
            },
            'confidence' => 1.0
          }
        end
      end

      def self.partition_x_bounds(params, wall_length)
        count = InteriorLayout.partition_count(params)
        bounds = [0.0]
        (1..count).each do |index|
          bounds << wall_length * index / (count + 1.0)
        end
        bounds << wall_length
        bounds
      end

      def self.room_polygon(bound)
        [
          [bound[:x_min], bound[:y_min], 0],
          [bound[:x_max], bound[:y_min], 0],
          [bound[:x_max], bound[:y_max], 0],
          [bound[:x_min], bound[:y_max], 0]
        ]
      end

      def self.room_area(bound)
        ((bound[:x_max] - bound[:x_min]) * (bound[:y_max] - bound[:y_min])).round(1)
      end

      def self.room_name(index, total)
        return 'Main Room' if total == 1

        format('Room %d', index + 1)
      end

      def self.zone_name(index, total)
        ZONE_NAMES[index] || format('zone_%02d', index + 1)
      end

      def self.partition_thickness(params)
        value = params['wall_thickness'] || params[:wall_thickness]
        value.nil? ? 240.0 : value.to_f
      end
    end
  end
end
