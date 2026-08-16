# frozen_string_literal: true

require_relative '../geometry/units'
require_relative '../metadata/attributes'

module Geomora
  module Generators
    module ElementSupport
      private

      def write_metadata(group, element, lod_level: nil)
        attrs = {
          entity_id: element.id,
          entity_type: element.type,
          schema_version: @schema_version,
          project_id: @project_id
        }
        attrs['lod_level'] = lod_level if lod_level
        Metadata::Attributes.write(group, attrs)
      end

      def to_len(mm)
        Geometry::Units.mm_to_length(mm)
      end

      def to_point(arr)
        Geom::Point3d.new(to_len(arr[0]), to_len(arr[1]), to_len(arr[2]))
      end

      def extrude_polygon(entities, polygon, thickness, direction: 1)
        pts = polygon.map { |p| to_point(p) }
        face = entities.add_face(pts)
        face.reverse! if face.normal.z * direction < 0
        face.pushpull(to_len(thickness) * direction)
        face
      end
    end
  end
end
