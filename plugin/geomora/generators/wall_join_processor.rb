# frozen_string_literal: true

module Geomora
  module Generators
    class WallJoinProcessor
      def self.join_walls(wall_groups, storey_group)
        groups = wall_groups.select { |group| group.valid? }
        return 0 if groups.length < 2

        intersections = 0
        groups.combination(2) do |wall_a, wall_b|
          wall_a.entities.intersect_with(
            false,
            wall_a.transformation,
            wall_b.entities,
            wall_b.transformation,
            true,
            storey_group.entities
          )
          intersections += 1
        end

        groups.each { |group| merge_coplanar_faces(group.entities) }
        intersections
      end

      def self.merge_coplanar_faces(entities)
        merged = 0
        entities.grep(Sketchup::Edge).each do |edge|
          next unless edge.valid? && edge.faces.length == 2

          face_a, face_b = edge.faces
          next unless coplanar_faces?(face_a, face_b)

          begin
            edge.erase!
            merged += 1
          rescue StandardError
            # locked geometry
          end
        end
        merged
      end

      def self.coplanar_faces?(face_a, face_b)
        return false unless face_a.valid? && face_b.valid?

        normal_a = face_a.normal
        normal_b = face_b.normal
        return false unless normal_a.parallel?(normal_b)

        plane = face_a.plane
        face_b.vertices.all? { |vertex| vertex.position.on_plane?(plane) }
      end
    end
  end
end
