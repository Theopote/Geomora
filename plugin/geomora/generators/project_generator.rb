# frozen_string_literal: true

require_relative 'building_generator'
require_relative '../core/lod_policy'
require_relative '../core/lod_visibility'
require_relative '../metadata/attributes'

module Geomora
  module Generators
    class ProjectGenerator
      def initialize(model)
        @model = model
      end

      def generate(document)
        Logger.info('Starting generation')

        remove_existing_project(document.project.id)

        context = build_context(document)
        project_group = create_project_group(document)

        building_gen = BuildingGenerator.new(@model, context)
        document.buildings.each do |building|
          building_gen.generate(building, project_group, document)
        end

        Core::LodVisibility.apply(@model, context[:lod_level])
        Logger.info('Generation complete')
        project_group
      end

      private

      def build_context(document)
        lod_level = Core::LodPolicy.normalize(document.project.lod_level)
        {
          tags: Tags::Manager.new(@model),
          component_manager: Components::ComponentManager.new(@model),
          project_id: document.project.id,
          schema_version: document.schema_version,
          lod_level: lod_level
        }
      end

      def create_project_group(document)
        group = @model.active_entities.add_group
        group.name = "Geomora Project: #{document.project.name}"

        Metadata::Attributes.write(group, {
          entity_id: document.project.id,
          entity_type: 'project',
          schema_version: document.schema_version,
          project_id: document.project.id,
          lod_level: Core::LodPolicy.normalize(document.project.lod_level)
        })

        @tags = Tags::Manager.new(@model)
        @tags.apply(group, 'Geomora_Reference')
        group
      end

      def remove_existing_project(project_id)
        to_remove = @model.active_entities.grep(Sketchup::Group).select do |entity|
          Metadata::Attributes.project_id(entity) == project_id &&
            Metadata::Attributes.read(entity, 'entity_type') == 'project'
        end

        to_remove.each do |entity|
          Logger.info("Removing existing project container: #{project_id}")
          entity.erase!
        end
      end
    end
  end
end
