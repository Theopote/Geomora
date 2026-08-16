# frozen_string_literal: true

require_relative 'element_support'

module Geomora
  module Generators
    class TrimGenerator
      include ElementSupport

      def initialize(model, tags:, project_id:, schema_version:, lod_level: 200)
        @model = model
        @tags = tags
        @project_id = project_id
        @schema_version = schema_version
        @lod_level = lod_level
      end

      def generate(trim, storey_elevation, parent_entities)
        Logger.debug("Generating #{trim.id}")

        group = parent_entities.add_group
        group.name = trim.id
        position = trim.geometry[:position]
        width = trim.geometry[:width].to_f
        height = trim.geometry[:height].to_f
        depth = trim.geometry[:depth].to_f
        x = position[0].to_f
        y = position[1].to_f
        z = storey_elevation + position[2].to_f

        polygon = [
          [x, y, z],
          [x + width, y, z],
          [x + width, y - depth, z],
          [x, y - depth, z]
        ]

        extrude_polygon(group.entities, polygon, height, direction: 1)
        write_metadata(group, trim, lod_level: @lod_level)
        @tags.apply(group, 'Geomora_Trim')
        group
      end
    end
  end
end
