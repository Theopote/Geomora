# frozen_string_literal: true

module Geomora
  module Core
    class StructuralGrid
      def self.enabled?(params)
        config = params['building_elements'] || params[:building_elements]
        return false unless config.is_a?(Hash)

        value = config['structural_grid'] || config[:structural_grid]
        value == true || value.to_s == 'true'
      end

      def self.column_positions(
        wall_length:,
        building_depth:,
        column_size:,
        grid_x_spacing:,
        grid_y_spacing:
      )
        span_x = [wall_length - column_size, 0].max
        span_y = [building_depth - column_size, 0].max
        xs = axis_positions(span_x, grid_x_spacing, 0)
        ys = axis_positions(span_y, grid_y_spacing, 0)

        xs.product(ys).map { |x, y| [x, y] }
      end

      def self.axis_positions(span, spacing, start)
        return [start] if span <= 0

        spacing = spacing.to_f
        return [start, span].uniq if spacing <= 0

        positions = [start]
        pos = spacing
        while pos < span
          positions << pos
          pos += spacing
        end
        positions << span unless positions.include?(span)
        positions
      end

      def self.column_elements(
        params:,
        wall_length:,
        building_depth:,
        column_size:,
        wall_height:,
        storey_id:,
        storey_index:,
        id_prefix: 'grid_col'
      )
        grid_x = float_param(params, 'grid_x_spacing', default_spacing(wall_length))
        grid_y = float_param(params, 'grid_y_spacing', default_spacing(building_depth))
        positions = column_positions(
          wall_length: wall_length,
          building_depth: building_depth,
          column_size: column_size,
          grid_x_spacing: grid_x,
          grid_y_spacing: grid_y
        )

        positions.each_with_index.map do |(x, y), index|
          {
            'id' => format('%s_%02d_%02d', id_prefix, storey_index + 1, index + 1),
            'type' => 'column',
            'storey_id' => storey_id,
            'geometry' => {
              'position' => [x, y, 0],
              'width' => column_size,
              'depth' => column_size,
              'height' => wall_height
            },
            'semantic' => { 'structural' => true, 'grid' => true },
            'confidence' => 1.0
          }
        end
      end

      def self.default_spacing(span)
        candidate = span / 2.0
        candidate.positive? ? candidate : 3000.0
      end

      def self.float_param(params, key, default)
        value = params[key]
        value.nil? ? default : value.to_f
      end
    end
  end
end
