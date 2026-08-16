# frozen_string_literal: true

module Geomora
  module Core
    class InteriorLayout
      def self.enabled?(params)
        config = params['building_elements'] || params[:building_elements]
        return false unless config.is_a?(Hash)

        value = config['interior_partitions'] || config[:interior_partitions]
        value == true || value.to_s == 'true'
      end

      def self.partition_walls(
        params:,
        wall_length:,
        wall_thickness:,
        building_depth:,
        storey_id:,
        storey_index:,
        wall_height:,
        perimeter_walls: false
      )
        count = partition_count(params)
        return [] if count < 1

        y_range = interior_y_range(building_depth, wall_thickness, perimeter_walls)
        suffix = format('%02d', storey_index + 1)
        thickness = partition_thickness(params, wall_thickness)

        (1..count).map do |index|
          x = wall_length * index / (count + 1.0)
          {
            'id' => format('partition_%s_%02d', suffix, index),
            'type' => 'wall',
            'storey_id' => storey_id,
            'geometry' => {
              'baseline' => [[x, y_range[:start], 0], [x, y_range[:end], 0]],
              'height' => wall_height,
              'thickness' => thickness
            },
            'semantic' => {
              'interior' => true,
              'partition' => true,
              'partition_index' => index
            },
            'opening_ids' => [],
            'confidence' => 1.0
          }
        end
      end

      def self.partition_count(params)
        value = params['partition_count'] || params[:partition_count]
        count = value.nil? ? 1 : value.to_i
        count < 1 ? 0 : count
      end

      def self.partition_thickness(params, default)
        value = params['partition_thickness'] || params[:partition_thickness]
        value.nil? ? default : value.to_f
      end

      def self.interior_y_range(building_depth, wall_thickness, perimeter_walls)
        if perimeter_walls
          half_depth = building_depth / 2.0
          half_thickness = wall_thickness / 2.0
          {
            start: half_thickness,
            end: half_depth - half_thickness
          }
        else
          inset = wall_thickness / 2.0
          {
            start: inset,
            end: building_depth - inset
          }
        end
      end
    end
  end
end
