# frozen_string_literal: true

require 'json'

module Geomora
  module Core
    class StructuralConstraintSolver
      DEFAULT_GRID_MM = 300.0

      def self.enabled?(params)
        config = params['building_elements'] || params[:building_elements]
        return false unless config.is_a?(Hash)

        value = config['structural_constraints'] || config[:structural_constraints]
        value == true || value.to_s == 'true'
      end

      def self.apply!(walls, params:)
        return walls unless enabled?(params)

        grid = grid_spacing(params)
        walls.map do |wall|
          next wall unless partition_wall?(wall)

          apply_parallel_constraint(wall, grid)
        end
      end

      def self.partition_wall?(wall)
        semantic = wall['semantic']
        semantic.is_a?(Hash) && semantic['partition'] == true
      end

      def self.apply_parallel_constraint(wall, grid)
        baseline = wall.dig('geometry', 'baseline')
        return wall unless baseline.is_a?(Array) && baseline.length == 2

        snapped = snap_baseline_to_grid(baseline, grid)
        wall = deep_dup_wall(wall)
        wall['geometry']['baseline'] = snapped
        semantic = wall['semantic'] || {}
        semantic['parallel'] = true
        semantic['grid_snapped'] = true
        wall['semantic'] = semantic
        wall
      end

      def self.snap_baseline_to_grid(baseline, grid)
        x = baseline[0][0].to_f
        snapped_x = (x / grid).round * grid
        dx = snapped_x - x
        [
          [baseline[0][0].to_f + dx, baseline[0][1].to_f, baseline[0][2].to_f],
          [baseline[1][0].to_f + dx, baseline[1][1].to_f, baseline[1][2].to_f]
        ]
      end

      def self.grid_spacing(params)
        value = params['partition_grid_spacing'] || params['grid_x_spacing'] || params[:grid_x_spacing]
        spacing = value.nil? ? DEFAULT_GRID_MM : value.to_f
        spacing.positive? ? spacing : DEFAULT_GRID_MM
      end

      def self.deep_dup_wall(wall)
        JSON.parse(JSON.generate(wall))
      end
    end
  end
end
