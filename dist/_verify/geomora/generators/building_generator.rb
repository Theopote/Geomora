# frozen_string_literal: true

require_relative 'storey_generator'
require_relative '../../metadata/attributes'

module Geomora
  module Generators
    class BuildingGenerator
      def initialize(model, context)
        @model = model
        @context = context
        @storey_gen = StoreyGenerator.new(model, context)
      end

      def generate(building, project_group, document)
        Logger.debug("Generating building #{building.id}")

        building_group = project_group.entities.add_group
        building_group.name = building.name

        Metadata::Attributes.write(building_group, {
          entity_id: building.id,
          entity_type: 'building',
          schema_version: @context[:schema_version],
          project_id: @context[:project_id]
        })

        building.storeys.each do |storey|
          @storey_gen.generate(storey, building_group, document)
        end

        building_group
      end
    end
  end
end
