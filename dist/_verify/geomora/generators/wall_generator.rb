# frozen_string_literal: true

require_relative '../../geometry/units'
require_relative '../../geometry/vectors'
require_relative '../../metadata/attributes'

module Geomora
  module Generators
    class WallGenerator
      def initialize(model, tags:, project_id:, schema_version:)
        @model = model
        @tags = tags
        @project_id = project_id
        @schema_version = schema_version
      end

      def generate(wall, storey_elevation, parent_entities)
        Logger.debug("Generating #{wall.id}")

        basis = Geometry::Vectors.wall_basis(wall.baseline)
        half_t = wall.thickness / 2.0
        wall_length = wall.length

        normal_offset = Geometry::Vectors.scale(basis[:normal], half_t)
        neg_normal = Geometry::Vectors.scale(basis[:normal], -half_t)

        z_base = storey_elevation
        start = basis[:start]
        end_along = Geometry::Vectors.add(
          [start[0], start[1], z_base],
          Geometry::Vectors.scale(basis[:along], wall_length)
        )

        corner_a = Geometry::Vectors.add(
          [start[0], start[1], z_base],
          neg_normal
        )
        corner_b = Geometry::Vectors.add(end_along, neg_normal)
        corner_c = Geometry::Vectors.add(end_along, normal_offset)
        corner_d = Geometry::Vectors.add(
          [start[0], start[1], z_base],
          normal_offset
        )

        group = parent_entities.add_group
        group.name = wall.id
        ents = group.entities

        pts = [corner_a, corner_b, corner_c, corner_d].map { |p| to_point(p) }
        bottom_face = ents.add_face(pts)
        bottom_face.reverse! if bottom_face.normal.z < 0

        bottom_face.pushpull(to_len(wall.height))

        Metadata::Attributes.write(group, entity_metadata(wall))

        @tags.apply(group, 'Geomora_Walls')
        group
      end

      private

      def entity_metadata(wall)
        {
          entity_id: wall.id,
          entity_type: wall.type,
          schema_version: @schema_version,
          project_id: @project_id
        }
      end

      def to_len(mm)
        Geometry::Units.mm_to_length(mm)
      end

      def to_point(arr)
        Geom::Point3d.new(to_len(arr[0]), to_len(arr[1]), to_len(arr[2]))
      end
    end
  end
end
