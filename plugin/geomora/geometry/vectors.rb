# frozen_string_literal: true

module Geomora
  module Geometry
  module Vectors
    class << self
      def subtract(a, b)
        [a[0] - b[0], a[1] - b[1], a[2] - b[2]]
      end

      def add(a, b)
        [a[0] + b[0], a[1] + b[1], a[2] + b[2]]
      end

      def scale(v, s)
        [v[0] * s, v[1] * s, v[2] * s]
      end

      def length(v)
        Math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)
      end

      def normalize(v)
        len = length(v)
        return [0.0, 0.0, 0.0] if len.zero?

        [v[0] / len, v[1] / len, v[2] / len]
      end

      def cross(a, b)
        [
          a[1] * b[2] - a[2] * b[1],
          a[2] * b[0] - a[0] * b[2],
          a[0] * b[1] - a[1] * b[0]
        ]
      end

      def dot(a, b)
        a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
      end

      # Wall runs along X-Y plane; Z is up.
      def wall_basis(baseline)
        start_pt = baseline[0]
        end_pt = baseline[1]
        along = normalize(subtract(end_pt, start_pt))
        up = [0.0, 0.0, 1.0]
        normal = normalize(cross(along, up))
        { start: start_pt, along: along, up: up, normal: normal }
      end
    end
  end
  end
end
