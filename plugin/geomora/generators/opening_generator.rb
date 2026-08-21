# frozen_string_literal: true

require_relative '../core/errors'
require_relative '../geometry/units'
require_relative '../geometry/vectors'

module Geomora
  module Generators
    class OpeningGenerator
      def initialize(model)
        @model = model
      end

      def cut_openings(wall_group, wall, openings, storey_elevation)
        return if openings.empty?

        basis = Geometry::Vectors.wall_basis(wall.baseline)
        half_t = wall.thickness / 2.0

        openings.each do |opening|
          Logger.debug("Cutting opening #{opening.id} in #{wall.id}")
          cut_opening(wall_group, wall, opening, basis, half_t, storey_elevation, wall.thickness)
        end
      end

      private

      def cut_opening(wall_group, wall, opening, basis, half_t, storey_elevation, wall_thickness)
        offset = opening.offset.to_f
        width = opening.width.to_f
        sill = opening.sill_height.to_f
        height = opening.height.to_f

        along_start = Geometry::Vectors.add(
          basis[:start],
          Geometry::Vectors.scale(basis[:along], offset)
        )
        along_end = Geometry::Vectors.add(
          basis[:start],
          Geometry::Vectors.scale(basis[:along], offset + width)
        )

        z_bottom = storey_elevation + sill
        z_top = z_bottom + height

        # Exterior face offset from centreline (baseline = centreline convention)
        ext_offset = Geometry::Vectors.scale(basis[:normal], half_t)

        pts = [
          point(along_start, z_bottom, ext_offset),
          point(along_end, z_bottom, ext_offset),
          point(along_end, z_top, ext_offset),
          point(along_start, z_top, ext_offset)
        ]

        ents = wall_group.entities
        opening_face = ents.add_face(pts)
        unless opening_face&.valid?
          raise GeometryGenerationError,
                "Failed to create opening #{opening.id} in wall #{wall.id}"
        end

        opening_face.pushpull(-to_len(wall_thickness))
      end

      def point(along_pt, z, normal_offset)
        arr = Geometry::Vectors.add([along_pt[0], along_pt[1], z], normal_offset)
        Geom::Point3d.new(to_len(arr[0]), to_len(arr[1]), to_len(arr[2]))
      end

      def to_len(mm)
        Geometry::Units.mm_to_length(mm)
      end
    end
  end
end
