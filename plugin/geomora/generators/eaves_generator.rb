# frozen_string_literal: true

require_relative 'element_support'

module Geomora
  module Generators
    class EavesGenerator
      include ElementSupport

      def initialize(model, tags:, project_id:, schema_version:, lod_level: 200)
        @model = model
        @tags = tags
        @project_id = project_id
        @schema_version = schema_version
        @lod_level = lod_level
      end

      def generate(eaves, storey_elevation, parent_entities)
        Logger.debug("Generating #{eaves.id}")

        group = parent_entities.add_group
        group.name = eaves.id
        polygon = eaves.geometry[:polygon]
        thickness = eaves.geometry[:thickness].to_f
        elevation = storey_elevation + eaves.geometry[:elevation].to_f
        projection = eaves.geometry[:projection].to_f
        y_front = polygon[0][1].to_f
        wall_length = polygon[1][0].to_f

        band = [
          [0, y_front, elevation],
          [wall_length, y_front, elevation],
          [wall_length, y_front - projection, elevation],
          [0, y_front - projection, elevation]
        ]

        extrude_polygon(group.entities, band, thickness, direction: 1)
        write_metadata(group, eaves, lod_level: @lod_level)
        @tags.apply(group, 'Geomora_Eaves')
        group
      end
    end
  end
end
