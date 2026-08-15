# frozen_string_literal: true

require_relative 'wall_generator'
require_relative 'opening_generator'
require_relative 'window_generator'
require_relative 'door_generator'
require_relative '../../metadata/attributes'

module Geomora
  module Generators
    class StoreyGenerator
      def initialize(model, context)
        @model = model
        @context = context
        @wall_gen = WallGenerator.new(
          model,
          tags: context[:tags],
          project_id: context[:project_id],
          schema_version: context[:schema_version]
        )
        @opening_gen = OpeningGenerator.new(model)
        @window_gen = WindowGenerator.new(
          model,
          component_manager: context[:component_manager],
          tags: context[:tags],
          project_id: context[:project_id],
          schema_version: context[:schema_version]
        )
        @door_gen = DoorGenerator.new(
          model,
          component_manager: context[:component_manager],
          tags: context[:tags],
          project_id: context[:project_id],
          schema_version: context[:schema_version]
        )
      end

      def generate(storey, building_group, document)
        Logger.debug("Generating storey #{storey.id}")

        storey_group = building_group.entities.add_group
        storey_group.name = storey.name

        Metadata::Attributes.write(storey_group, {
          entity_id: storey.id,
          entity_type: 'storey',
          schema_version: @context[:schema_version],
          project_id: @context[:project_id]
        })

        storey.elements.each do |element|
          case element.type
          when 'wall'
            generate_wall(element, storey, storey_group, document)
          end
        end

        storey_group
      end

      private

      def generate_wall(wall, storey, storey_group, document)
        wall_group = @wall_gen.generate(wall, storey.elevation, storey_group.entities)

        openings = document.openings.select { |o| wall.opening_ids.include?(o.id) }
        @opening_gen.cut_openings(wall_group, wall, openings, storey.elevation)

        openings.each do |opening|
          case opening.type
          when 'window'
            @window_gen.generate(opening, wall, storey.elevation, storey_group.entities)
          when 'door'
            @door_gen.generate(opening, wall, storey.elevation, storey_group.entities)
          end
        end
      end
    end
  end
end
