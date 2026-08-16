# frozen_string_literal: true

module Geomora
  module Core
    class BuildingComposer
      SUPPORTED_ELEMENTS = %w[floor roof column beam stair balcony parapet cornice].freeze

      def self.compose(params, wall_length:, wall_height:, wall_thickness:, storey_id:, storey_index: 0, top_storey: true)
        new(params, wall_length: wall_length, wall_height: wall_height,
            wall_thickness: wall_thickness, storey_id: storey_id,
            storey_index: storey_index, top_storey: top_storey).compose
      end

      def initialize(params, wall_length:, wall_height:, wall_thickness:, storey_id:, storey_index: 0, top_storey: true)
        @params = params.is_a?(Hash) ? params : {}
        @wall_length = wall_length
        @wall_height = wall_height
        @wall_thickness = wall_thickness
        @storey_id = storey_id
        @storey_index = storey_index
        @top_storey = top_storey
      end

      def compose
        elements = []
        elements << floor_element if enabled?(:floor)
        elements << roof_element if enabled?(:roof) && @top_storey
        elements.concat(column_elements) if enabled?(:columns)
        elements << beam_element if enabled?(:beam)
        elements << stair_element if enabled?(:stair) && stair_for_storey?
        elements << balcony_element if enabled?(:balcony) && facade_storey?
        elements << parapet_element if enabled?(:parapet) && @top_storey
        elements << cornice_element if enabled?(:cornice) && facade_storey?
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

      def int_param(key, default)
        value = @params[key]
        value.nil? ? default : value.to_i
      end

      def element_id(prefix)
        format('%s_%02d', prefix, @storey_index + 1)
      end

      def facade_storey?
        @storey_index.zero?
      end

      def stair_for_storey?
        storey_count <= 1 || @storey_index < storey_count - 1
      end

      def storey_count
        count = int_param('storey_count', 1)
        count < 1 ? 1 : count
      end

      def perimeter_walls_enabled?
        enabled?(:perimeter_walls)
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
          'id' => element_id('floor'),
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
          'id' => element_id('roof'),
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
        if perimeter_walls_enabled?
          half_depth = building_depth / 2.0
          y_front = 0
          y_back = building_depth - size
          x_right = @wall_length - size
          [
            column_at(element_id('column_a'), 0, y_front, size),
            column_at(element_id('column_b'), x_right, y_front, size),
            column_at(element_id('column_c'), 0, y_back, size),
            column_at(element_id('column_d'), x_right, y_back, size)
          ]
        else
          [
            column_at(element_id('column_a'), 0, 0, size),
            column_at(element_id('column_b'), @wall_length - size, 0, size)
          ]
        end
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
          'id' => element_id('beam'),
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
        rise = storey_count > 1 ? @wall_height : float_param('stair_rise', @wall_height / 2.0)
        width = float_param('stair_width', 1200)
        steps = int_param('stair_steps', 12)
        origin_x = [@wall_length - run, 0].max

        {
          'id' => element_id('stair'),
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

      def first_window
        windows = @params['windows']
        return nil unless windows.is_a?(Array)

        windows.find { |win| win.is_a?(Hash) && win['width'].to_f.positive? }
      end

      def balcony_element
        win = first_window
        offset = win ? win['offset'].to_f : 2000
        width = win ? win['width'].to_f : 2000
        sill = win ? (win['sill_height'] || 900).to_f : 900
        depth = float_param('balcony_depth', 1500)
        thickness = float_param('balcony_thickness', 150)

        {
          'id' => element_id('balcony'),
          'type' => 'balcony',
          'storey_id' => @storey_id,
          'geometry' => {
            'position' => [offset, 0, sill],
            'width' => width,
            'depth' => depth,
            'thickness' => thickness,
            'direction' => -1
          },
          'semantic' => { 'exterior' => true },
          'confidence' => 1.0
        }
      end

      def parapet_element
        half_depth = building_depth / 2.0
        top_z = @wall_height + roof_thickness
        height = float_param('parapet_height', 900)
        thickness = float_param('parapet_thickness', 200)

        {
          'id' => element_id('parapet'),
          'type' => 'parapet',
          'storey_id' => @storey_id,
          'geometry' => {
            'baseline' => [[0, -half_depth, top_z], [@wall_length, -half_depth, top_z]],
            'height' => height,
            'thickness' => thickness
          },
          'semantic' => { 'exterior' => true },
          'confidence' => 1.0
        }
      end

      def cornice_element
        cornice_height = float_param('cornice_height', 250)
        projection = float_param('cornice_projection', 300)
        z = @wall_height - cornice_height

        {
          'id' => element_id('cornice'),
          'type' => 'cornice',
          'storey_id' => @storey_id,
          'geometry' => {
            'baseline' => [[0, 0, z], [@wall_length, 0, z]],
            'width' => @wall_thickness,
            'height' => cornice_height,
            'projection' => projection
          },
          'semantic' => { 'exterior' => true },
          'confidence' => 1.0
        }
      end
    end
  end
end
