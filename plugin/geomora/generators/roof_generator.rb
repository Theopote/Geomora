# frozen_string_literal: true

require_relative 'element_support'

module Geomora
  module Generators
    class RoofGenerator
      include ElementSupport

      def initialize(model, tags:, project_id:, schema_version:)
        @model = model
        @tags = tags
        @project_id = project_id
        @schema_version = schema_version
      end

      def generate(roof, storey_elevation, parent_entities)
        Logger.debug("Generating #{roof.id}")

        group = parent_entities.add_group
        group.name = roof.id
        polygon = roof.geometry[:polygon]
        thickness = roof.geometry[:thickness].to_f
        z = storey_elevation + roof.geometry[:elevation].to_f
        elevated = polygon.map { |point| [point[0], point[1], z] }

        extrude_polygon(group.entities, elevated, thickness, direction: 1)
        write_metadata(group, roof)
        @tags.apply(group, 'Geomora_Roofs')
        group
      end
    end
  end
end
