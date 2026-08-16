# frozen_string_literal: true

module Geomora
  module Core
    class WallEnclosure
      def self.enabled?(params)
        config = params['building_elements'] || params[:building_elements]
        return false unless config.is_a?(Hash)

        value = config['perimeter_walls'] || config[:perimeter_walls]
        value == true || value.to_s == 'true'
      end

      def self.perimeter_walls(
        wall_length:,
        wall_thickness:,
        building_depth:,
        storey_id:,
        storey_index:,
        wall_height:,
        facade_wall_id:,
        facade_semantic: nil
      )
        half_depth = building_depth / 2.0
        half_thickness = wall_thickness / 2.0
        y_back = half_depth - half_thickness
        y_front_inner = half_thickness
        suffix = format('%02d', storey_index + 1)

        facade = {
          'id' => facade_wall_id,
          'type' => 'wall',
          'storey_id' => storey_id,
          'geometry' => {
            'baseline' => [[0, 0, 0], [wall_length, 0, 0]],
            'height' => wall_height,
            'thickness' => wall_thickness
          },
          'semantic' => facade_semantic || default_semantic('facade'),
          'opening_ids' => [],
          'confidence' => 1.0
        }

        [
          facade,
          wall_element(
            id: "wall_#{suffix}_back",
            storey_id: storey_id,
            baseline: [[0, y_back, 0], [wall_length, y_back, 0]],
            wall_height: wall_height,
            wall_thickness: wall_thickness,
            role: 'back'
          ),
          wall_element(
            id: "wall_#{suffix}_left",
            storey_id: storey_id,
            baseline: [[half_thickness, y_front_inner, 0], [half_thickness, y_back, 0]],
            wall_height: wall_height,
            wall_thickness: wall_thickness,
            role: 'left'
          ),
          wall_element(
            id: "wall_#{suffix}_right",
            storey_id: storey_id,
            baseline: [[wall_length - half_thickness, y_back, 0], [wall_length - half_thickness, y_front_inner, 0]],
            wall_height: wall_height,
            wall_thickness: wall_thickness,
            role: 'right'
          )
        ]
      end

      def self.wall_element(id:, storey_id:, baseline:, wall_height:, wall_thickness:, role:)
        {
          'id' => id,
          'type' => 'wall',
          'storey_id' => storey_id,
          'geometry' => {
            'baseline' => baseline,
            'height' => wall_height,
            'thickness' => wall_thickness
          },
          'semantic' => default_semantic(role),
          'opening_ids' => [],
          'confidence' => 1.0
        }
      end

      def self.default_semantic(role)
        {
          'exterior' => true,
          'join_group' => 'perimeter',
          'join_role' => role
        }
      end
    end
  end
end
