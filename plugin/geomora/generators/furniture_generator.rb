# frozen_string_literal: true

require_relative 'element_support'

module Geomora
  module Generators
    class FurnitureGenerator
      include ElementSupport

      def initialize(model, tags:, project_id:, schema_version:)
        @model = model
        @tags = tags
        @project_id = project_id
        @schema_version = schema_version
      end

      def generate(item, storey_elevation, parent_entities)
        Logger.debug("Generating #{item.id}")

        group = parent_entities.add_group
        kind = item.semantic.is_a?(Hash) ? (item.semantic[:kind] || item.semantic['kind']) : 'furniture'
        group.name = "#{item.id} (#{kind})"
        position = item.geometry[:position]
        width = item.geometry[:width].to_f
        depth = item.geometry[:depth].to_f
        height = item.geometry[:height].to_f
        x = position[0].to_f
        y = position[1].to_f
        z = storey_elevation + position[2].to_f
        polygon = [
          [x, y, z],
          [x + width, y, z],
          [x + width, y + depth, z],
          [x, y + depth, z]
        ]

        extrude_polygon(group.entities, polygon, height, direction: 1)
        write_furniture_metadata(group, item)
        @tags.apply(group, 'Geomora_Furniture')
        group
      end

      private

      def write_furniture_metadata(group, item)
        attrs = {
          entity_id: item.id,
          entity_type: item.type,
          schema_version: @schema_version,
          project_id: @project_id,
          room_id: item.room_id
        }
        semantic = item.semantic
        if semantic.is_a?(Hash)
          attrs['furniture_kind'] = semantic['kind'] || semantic[:kind]
          attrs['room_type'] = semantic['room_type'] || semantic[:room_type]
        end
        Metadata::Attributes.write(group, attrs)
      end
    end
  end
end
