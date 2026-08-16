# frozen_string_literal: true

require_relative 'element_support'

module Geomora
  module Generators
    class FloorGenerator
      include ElementSupport

      def initialize(model, tags:, project_id:, schema_version:)
        @model = model
        @tags = tags
        @project_id = project_id
        @schema_version = schema_version
      end

      def generate(floor, storey_elevation, parent_entities)
        Logger.debug("Generating #{floor.id}")

        group = parent_entities.add_group
        group.name = floor.id
        polygon = floor.geometry[:polygon]
        thickness = floor.geometry[:thickness].to_f
        z = storey_elevation + (floor.geometry[:elevation] || 0).to_f
        elevated = polygon.map { |point| [point[0], point[1], z] }

        extrude_polygon(group.entities, elevated, thickness, direction: -1)
        write_metadata(group, floor)
        @tags.apply(group, 'Geomora_Floors')
        group
      end
    end
  end
end
