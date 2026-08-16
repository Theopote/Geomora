# frozen_string_literal: true

module Geomora
  module Core
    class ConstraintSolver
      SUPPORTED_TYPES = %w[
        equal_width equal_height equal_spacing align symmetry fixed_dimension
      ].freeze

      def self.solve(params, grid_mm: Rationalizer::DEFAULT_GRID_MM)
        new(params, grid_mm: grid_mm).solve
      end

      def initialize(params, grid_mm: Rationalizer::DEFAULT_GRID_MM)
        @params = params.is_a?(Hash) ? params : {}
        @grid_mm = grid_mm.to_f
        @grid_mm = Rationalizer::DEFAULT_GRID_MM if @grid_mm <= 0
      end

      def solve
        windows = normalize_windows(@params['windows'])
        door = normalize_door(@params['door'])
        constraints = explicit_constraints
        wall_length = float_param('wall_length', 10_000)
        solved = []

        constraints.each do |constraint|
          next unless SUPPORTED_TYPES.include?(constraint['type'])

          windows = apply_constraint(windows, constraint, door, wall_length)
          solved << constraint['type']
        end

        {
          'windows' => windows,
          'door' => door,
          'constraint_solution' => {
            'method' => 'facade_constraint_v1',
            'constraints_solved' => solved.uniq,
            'grid_mm' => @grid_mm
          }
        }
      end

      private

      def explicit_constraints
        constraints = @params['constraints']
        return [] unless constraints.is_a?(Array)

        constraints.select { |constraint| constraint.is_a?(Hash) && constraint['type'] }
      end

      def normalize_windows(raw)
        return [] unless raw.is_a?(Array)

        raw.map do |win|
          next unless win.is_a?(Hash)

          {
            'offset' => win['offset'].to_f,
            'width' => win['width'].to_f,
            'height' => win['height'].to_f,
            'sill_height' => (win['sill_height'] || 0).to_f,
            'confidence' => win['confidence'],
            'bbox_norm' => win['bbox_norm']
          }.compact
        end.compact
      end

      def normalize_door(raw)
        return empty_door unless raw.is_a?(Hash)

        {
          'offset' => raw['offset'].to_f,
          'width' => raw['width'].to_f,
          'height' => raw['height'].to_f
        }
      end

      def apply_constraint(windows, constraint, door, wall_length)
        case constraint['type']
        when 'equal_width'
          apply_equal_width(windows)
        when 'equal_height'
          apply_equal_height(windows)
        when 'align'
          apply_align(windows)
        when 'equal_spacing'
          layout_equal_spacing(windows, wall_length, door)
        when 'symmetry'
          layout_symmetry(windows, wall_length, door)
        when 'fixed_dimension'
          windows
        else
          windows
        end
      end

      def apply_equal_width(windows)
        width = snap(median(windows.map { |win| win['width'].to_f }))
        windows.map { |win| win.merge('width' => width) }
      end

      def apply_equal_height(windows)
        height = snap(median(windows.map { |win| win['height'].to_f }))
        windows.map { |win| win.merge('height' => height) }
      end

      def apply_align(windows)
        sill = snap(median(windows.map { |win| win['sill_height'].to_f }))
        windows.map { |win| win.merge('sill_height' => sill) }
      end

      def layout_equal_spacing(windows, wall_length, door)
        Rationalizer.new(
          @params.merge('wall_length' => wall_length, 'door' => door),
          grid_mm: @grid_mm
        ).layout_equal_spacing(windows, wall_length, door)
      end

      def layout_symmetry(windows, wall_length, door)
        layout_equal_spacing(windows, wall_length, door)
      end

      def float_param(key, default)
        value = @params[key]
        value.nil? ? default : value.to_f
      end

      def median(values)
        sorted = values.map(&:to_f).sort
        return 0.0 if sorted.empty?

        mid = sorted.length / 2
        if sorted.length.odd?
          sorted[mid]
        else
          (sorted[mid - 1] + sorted[mid]) / 2.0
        end
      end

      def snap(value)
        ((value.to_f / @grid_mm).round * @grid_mm).round(1)
      end

      def empty_door
        { 'offset' => 0, 'width' => 0, 'height' => 0 }
      end
    end
  end
end
