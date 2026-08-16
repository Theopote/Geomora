# frozen_string_literal: true

require_relative 'element_support'
require_relative '../geometry/vectors'

module Geomora
  module Generators
    class CorniceGenerator
      include ElementSupport

      def initialize(model, tags:, project_id:, schema_version:)
        @model = model
        @tags = tags
        @project_id = project_id
        @schema_version = schema_version
      end

      def generate(cornice, storey_elevation, parent_entities)
        Logger.debug("Generating #{cornice.id}")

        group = parent_entities.add_group
        group.name = cornice.id
        baseline = cornice.geometry[:baseline]
        width = cornice.geometry[:width].to_f
        height = cornice.geometry[:height].to_f
        projection = cornice.geometry[:projection].to_f
        basis = Geometry::Vectors.wall_basis(baseline)
        z = storey_elevation + baseline[0][2].to_f
        start = [baseline[0][0], baseline[0][1], z]
        length = Math.sqrt(
          (baseline[1][0] - baseline[0][0])**2 +
          (baseline[1][1] - baseline[0][1])**2
        )
        end_point = Geometry::Vectors.add(start, Geometry::Vectors.scale(basis[:along], length))
        outward = Geometry::Vectors.scale(basis[:normal], projection)
        neg_half = Geometry::Vectors.scale(basis[:normal], -width / 2.0)
        pos_half = Geometry::Vectors.scale(basis[:normal], width / 2.0)

        band_start = Geometry::Vectors.add(start, neg_half)
        band_end = Geometry::Vectors.add(end_point, neg_half)
        outer_start = Geometry::Vectors.add(band_start, outward)
        outer_end = Geometry::Vectors.add(band_end, outward)

        corners = [
          band_start,
          band_end,
          outer_end,
          outer_start
        ]

        extrude_polygon(group.entities, corners, height, direction: 1)
        write_metadata(group, cornice)
        @tags.apply(group, 'Geomora_Cornices')
        group
      end
    end
  end
end
