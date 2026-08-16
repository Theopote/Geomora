# frozen_string_literal: true

require_relative 'element_support'
require_relative '../geometry/vectors'

module Geomora
  module Generators
    class RailingGenerator
      include ElementSupport

      def initialize(model, tags:, project_id:, schema_version:, lod_level: 200)
        @model = model
        @tags = tags
        @project_id = project_id
        @schema_version = schema_version
        @lod_level = lod_level
      end

      def generate(railing, storey_elevation, parent_entities)
        Logger.debug("Generating #{railing.id}")

        group = parent_entities.add_group
        group.name = railing.id
        baseline = railing.geometry[:baseline]
        height = railing.geometry[:height].to_f
        thickness = railing.geometry[:thickness].to_f
        basis = Geometry::Vectors.wall_basis(baseline)
        z = storey_elevation + baseline[0][2].to_f
        start = [baseline[0][0], baseline[0][1], z]
        length = Math.sqrt(
          (baseline[1][0] - baseline[0][0])**2 +
          (baseline[1][1] - baseline[0][1])**2
        )
        end_point = Geometry::Vectors.add(start, Geometry::Vectors.scale(basis[:along], length))
        outward = Geometry::Vectors.scale(basis[:normal], thickness / 2.0)
        neg_outward = Geometry::Vectors.scale(basis[:normal], -thickness / 2.0)

        corners = [
          Geometry::Vectors.add(start, neg_outward),
          Geometry::Vectors.add(end_point, neg_outward),
          Geometry::Vectors.add(end_point, outward),
          Geometry::Vectors.add(start, outward)
        ]

        extrude_polygon(group.entities, corners, height, direction: 1)
        write_metadata(group, railing, lod_level: @lod_level)
        @tags.apply(group, 'Geomora_Railings')
        group
      end
    end
  end
end
