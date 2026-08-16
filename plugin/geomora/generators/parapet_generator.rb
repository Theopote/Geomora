# frozen_string_literal: true

require_relative 'element_support'
require_relative '../geometry/vectors'

module Geomora
  module Generators
    class ParapetGenerator
      include ElementSupport

      def initialize(model, tags:, project_id:, schema_version:)
        @model = model
        @tags = tags
        @project_id = project_id
        @schema_version = schema_version
      end

      def generate(parapet, storey_elevation, parent_entities)
        Logger.debug("Generating #{parapet.id}")

        group = parent_entities.add_group
        group.name = parapet.id
        baseline = parapet.geometry[:baseline]
        height = parapet.geometry[:height].to_f
        thickness = parapet.geometry[:thickness].to_f
        basis = Geometry::Vectors.wall_basis(baseline)
        half_t = thickness / 2.0
        z = storey_elevation + baseline[0][2].to_f
        start = [baseline[0][0], baseline[0][1], z]
        length = Math.sqrt(
          (baseline[1][0] - baseline[0][0])**2 +
          (baseline[1][1] - baseline[0][1])**2
        )
        end_point = Geometry::Vectors.add(start, Geometry::Vectors.scale(basis[:along], length))
        normal = Geometry::Vectors.scale(basis[:normal], half_t)
        neg_normal = Geometry::Vectors.scale(basis[:normal], -half_t)

        corners = [
          Geometry::Vectors.add(start, neg_normal),
          Geometry::Vectors.add(end_point, neg_normal),
          Geometry::Vectors.add(end_point, normal),
          Geometry::Vectors.add(start, normal)
        ]

        extrude_polygon(group.entities, corners, height, direction: 1)
        write_metadata(group, parapet)
        @tags.apply(group, 'Geomora_Parapets')
        group
      end
    end
  end
end
