# frozen_string_literal: true

module Geomora
  module Geometry
    module Polygon
      class << self
        def rectangle_points(origin, width_vec, height_vec)
          o = origin
          w = width_vec
          h = height_vec
          [
            o,
            [o[0] + w[0], o[1] + w[1], o[2] + w[2]],
            [o[0] + w[0] + h[0], o[1] + w[1] + h[1], o[2] + w[2] + h[2]],
            [o[0] + h[0], o[1] + h[1], o[2] + h[2]]
          ]
        end
      end
    end
  end
end
