# frozen_string_literal: true

require_relative 'element_support'

module Geomora
  module Generators
    class RoomGenerator
      include ElementSupport

      ZONE_THICKNESS_MM = 5.0

      def initialize(model, tags:, project_id:, schema_version:)
        @model = model
        @tags = tags
        @project_id = project_id
        @schema_version = schema_version
      end

      def generate(room, storey_elevation, parent_entities)
        Logger.debug("Generating #{room.id}")

        group = parent_entities.add_group
        group.name = room.name
        polygon = room.geometry[:polygon]
        z = storey_elevation + (room.geometry[:elevation] || 0).to_f + 1.0
        elevated = polygon.map { |point| [point[0], point[1], z] }

        extrude_polygon(group.entities, elevated, ZONE_THICKNESS_MM, direction: 1)
        write_room_metadata(group, room)
        @tags.apply(group, 'Geomora_Rooms')
        group
      end

      private

      def write_room_metadata(group, room)
        attrs = {
          entity_id: room.id,
          entity_type: 'room',
          schema_version: @schema_version,
          project_id: @project_id,
          room_name: room.name
        }
        semantic = room.semantic
        if semantic.is_a?(Hash)
          attrs['zone'] = semantic['zone'] || semantic[:zone]
          attrs['room_type'] = semantic['room_type'] || semantic[:room_type]
        end
        Metadata::Attributes.write(group, attrs)
      end
    end
  end
end
