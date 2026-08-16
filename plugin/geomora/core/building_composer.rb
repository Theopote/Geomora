# frozen_string_literal: true

module Geomora
  module Core
    class BuildingComposer
      SUPPORTED_ELEMENTS = %w[floor roof column beam stair].freeze

      def self.compose(params, wall_length:, wall_height:, wall_thickness:, storey_id:)
        new(params, wall_length: wall_length, wall_height: wall_height,
            wall_thickness: wall_thickness, storey_id: storey_id).compose
      end

      def initialize(params, wall_length:, wall_height:, wall_thickness:, storey_id:)
        @params = params.is_a?(Hash) ? params : {}
        @wall_length = wall_length
        @wall_height = wall_height
        @wall_thickness = wall_thickness
        @storey_id = storey_id
      end

      def compose
        elements = []
        elements << floor_element if enabled?(:floor)
        elements << roof_element if enabled?(:roof)
        elements.concat(column_elements) if enabled?(:columns)
        elements << beam_element if enabled?(:beam)
        elements << stair_element if enabled?(:stair)
        elements
      end

      private

      def enabled?(key)
        config = building_elements
        return false unless config.is_a?(Hash)

        value = config[key.to_s]
        value = config[key.to_sym] if value.nil?
        value == true || value.to_s == 'true'
      end

      def building_elements
        @params['building_elements'] || @params[:building_elements]
      end

      def building_depth
        float_param('building_depth', 6000)
      end

      def slab_thickness
        float_param('slab_thickness', 200)
      end

      def roof_thickness
        float_param('roof_thickness', 200)
      end

      def column_size
        float_param('column_size', 400)
      end

      def float_param(key, default)
        value = @params[key]
        value.nil? ? default : value.to_f
      end

      def footprint_polygon
        half_depth = building_depth / 2.0
        [
          [0, -half_depth, 0],
          [@wall_length, -half_depth, 0],
          [@wall_length, half_depth, 0],
          [0, half_depth, 0]
        ]
      end

      def floor_element
        {
          'id' => 'floor_001',
          'type' => 'floor',
          'storey_id' => @storey_id,
          'geometry' => {
            'polygon' => footprint_polygon,
            'thickness' => slab_thickness,
            'elevation' => 0
          },
          'semantic' => { 'structural' => true },
          'confidence' => 1.0
        }
      end

      def roof_element
        {
          'id' => 'roof_001',
          'type' => 'roof',
          'storey_id' => @storey_id,
          'geometry' => {
            'polygon' => footprint_polygon,
            'thickness' => roof_thickness,
            'elevation' => @wall_height
          },
          'semantic' => { 'exterior' => true },
          'confidence' => 1.0
        }
      end

      def column_elements
        size = column_size
        [
          column_at('column_001', 0, 0, size),
          column_at('column_002', @wall_length - size, 0, size)
        ]
      end

      def column_at(id, x, y, size)
        {
          'id' => id,
          'type' => 'column',
          'storey_id' => @storey_id,
          'geometry' => {
            'position' => [x, y, 0],
            'width' => size,
            'depth' => size,
            'height' => @wall_height
          },
          'semantic' => { 'structural' => true },
          'confidence' => 1.0
        }
      end

      def beam_element
        {
          'id' => 'beam_001',
          'type' => 'beam',
          'storey_id' => @storey_id,
          'geometry' => {
            'baseline' => [[0, 0, @wall_height], [@wall_length, 0, @wall_height]],
            'width' => @wall_thickness,
            'height' => 300
          },
          'semantic' => { 'structural' => true },
          'confidence' => 1.0
        }
      end

      def stair_element
        run = float_param('stair_run', 3000)
        rise = float_param('stair_rise', @wall_height / 2.0)
        width = float_param('stair_width', 1200)
        steps = int_param('stair_steps', 12)
        origin_x = [@wall_length - run, 0].max

        {
          'id' => 'stair_001',
          'type' => 'stair',
          'storey_id' => @storey_id,
          'geometry' => {
            'origin' => [origin_x, -width / 2.0, 0],
            'width' => width,
            'run' => run,
            'rise' => rise,
            'steps' => steps
          },
          'semantic' => { 'circulation' => true },
          'confidence' => 1.0
        }
      end

      def int_param(key, default)
        value = @params[key]
        value.nil? ? default : value.to_i
      end
    end
  end
end
