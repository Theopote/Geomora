# frozen_string_literal: true

module Geomora
  module Geometry
    module Units
      SUPPORTED_UNITS = %w[mm].freeze

      def self.to_mm(value, unit)
        case unit
        when 'mm'
          value.to_f
        else
          raise UnsupportedSchemaError, "Unsupported unit: #{unit}"
        end
      end

      # SketchUp internal length unit is inches.
      def self.mm_to_inches(mm)
        mm.to_f / 25.4
      end

      def self.mm_to_length(mm)
        mm_to_inches(mm)
      end
    end
  end
end
