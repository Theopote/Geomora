# frozen_string_literal: true

require_relative 'wall_generator'
require_relative 'opening_generator'
require_relative 'window_generator'
require_relative 'door_generator'
require_relative 'floor_generator'
require_relative 'roof_generator'
require_relative 'column_generator'
require_relative 'beam_generator'
require_relative 'stair_generator'
require_relative 'balcony_generator'
require_relative 'parapet_generator'
require_relative 'cornice_generator'
require_relative 'trim_generator'
require_relative 'railing_generator'
require_relative 'eaves_generator'
require_relative 'room_generator'
require_relative 'furniture_generator'
require_relative 'wall_join_processor'
require_relative '../core/lod_policy'
require_relative '../metadata/attributes'

module Geomora
  module Generators
    class StoreyGenerator
      def initialize(model, context)
        @model = model
        @context = context
        @lod_level = context[:lod_level] || Core::LodPolicy::DEFAULT_LEVEL

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
          schema_version: context[:schema_version],
          lod_level: @lod_level
        )
        @door_gen = DoorGenerator.new(
          model,
          component_manager: context[:component_manager],
          tags: context[:tags],
          project_id: context[:project_id],
          schema_version: context[:schema_version]
        )
        @floor_gen = FloorGenerator.new(
          model,
          tags: context[:tags],
          project_id: context[:project_id],
          schema_version: context[:schema_version]
        )
        @roof_gen = RoofGenerator.new(
          model,
          tags: context[:tags],
          project_id: context[:project_id],
          schema_version: context[:schema_version]
        )
        @column_gen = ColumnGenerator.new(
          model,
          tags: context[:tags],
          project_id: context[:project_id],
          schema_version: context[:schema_version]
        )
        @beam_gen = BeamGenerator.new(
          model,
          tags: context[:tags],
          project_id: context[:project_id],
          schema_version: context[:schema_version]
        )
        @stair_gen = StairGenerator.new(
          model,
          tags: context[:tags],
          project_id: context[:project_id],
          schema_version: context[:schema_version]
        )
        @balcony_gen = BalconyGenerator.new(
          model,
          tags: context[:tags],
          project_id: context[:project_id],
          schema_version: context[:schema_version]
        )
        @parapet_gen = ParapetGenerator.new(
          model,
          tags: context[:tags],
          project_id: context[:project_id],
          schema_version: context[:schema_version]
        )
        @cornice_gen = CorniceGenerator.new(
          model,
          tags: context[:tags],
          project_id: context[:project_id],
          schema_version: context[:schema_version]
        )
        @trim_gen = TrimGenerator.new(
          model,
          tags: context[:tags],
          project_id: context[:project_id],
          schema_version: context[:schema_version],
          lod_level: @lod_level
        )
        @railing_gen = RailingGenerator.new(
          model,
          tags: context[:tags],
          project_id: context[:project_id],
          schema_version: context[:schema_version],
          lod_level: @lod_level
        )
        @eaves_gen = EavesGenerator.new(
          model,
          tags: context[:tags],
          project_id: context[:project_id],
          schema_version: context[:schema_version],
          lod_level: @lod_level
        )
        @room_gen = RoomGenerator.new(
          model,
          tags: context[:tags],
          project_id: context[:project_id],
          schema_version: context[:schema_version]
        )
        @furniture_gen = FurnitureGenerator.new(
          model,
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
          project_id: @context[:project_id],
          lod_level: @lod_level
        })

        joinable_wall_groups = []

        storey.elements.each do |element|
          case element.type
          when 'wall'
            wall_group = generate_wall(element, storey, storey_group, document)
            joinable_wall_groups << wall_group if wall_joinable?(element)
          when 'floor'
            @floor_gen.generate(element, storey.elevation, storey_group.entities)
          when 'roof'
            @roof_gen.generate(element, storey.elevation, storey_group.entities)
          when 'column'
            @column_gen.generate(element, storey.elevation, storey_group.entities)
          when 'beam'
            @beam_gen.generate(element, storey.elevation, storey_group.entities)
          when 'stair'
            @stair_gen.generate(element, storey.elevation, storey_group.entities)
          when 'balcony'
            @balcony_gen.generate(element, storey.elevation, storey_group.entities)
          when 'parapet'
            @parapet_gen.generate(element, storey.elevation, storey_group.entities)
          when 'cornice'
            @cornice_gen.generate(element, storey.elevation, storey_group.entities)
          when 'trim'
            @trim_gen.generate(element, storey.elevation, storey_group.entities)
          when 'railing'
            @railing_gen.generate(element, storey.elevation, storey_group.entities)
          when 'eaves'
            @eaves_gen.generate(element, storey.elevation, storey_group.entities)
          end
        end

        if joinable_wall_groups.length > 1
          WallJoinProcessor.join_walls(joinable_wall_groups, storey_group)
        end

        storey_rooms(document, storey).each do |room|
          next unless Core::LodPolicy.include_element?(:room, @lod_level)

          @room_gen.generate(room, storey.elevation, storey_group.entities)
        end

        storey_furniture(document, storey).each do |item|
          next unless item_visible?(item)

          @furniture_gen.generate(item, storey.elevation, storey_group.entities)
        end

        storey_group
      end

      private

      def storey_furniture(document, storey)
        items = document.furniture || []
        items.select { |item| item.storey_id == storey.id }
      end

      def item_visible?(item)
        type = item.type.to_s
        return Core::LodPolicy.include_element?(:fixture, @lod_level) if type == 'fixture'

        Core::LodPolicy.include_element?(:furniture, @lod_level)
      end

      def storey_rooms(document, storey)
        rooms = document.rooms || []
        rooms.select { |room| room.storey_id == storey.id }
      end

      def wall_joinable?(wall)
        semantic = wall.semantic
        return false unless semantic.is_a?(Hash)

        group = semantic['join_group'] || semantic[:join_group]
        !group.nil? && !group.to_s.empty?
      end

      def generate_wall(wall, storey, storey_group, document)
        wall_group = @wall_gen.generate(wall, storey.elevation, storey_group.entities)

        unless Core::LodPolicy.include_openings?(@lod_level)
          return wall_group
        end

        openings = document.openings.select { |o| wall.opening_ids.include?(o.id) }
        @opening_gen.cut_openings(wall_group, wall, openings, storey.elevation)

        openings.each do |opening|
          evidence = opening_evidence(opening, document)
          case opening.type
          when 'window'
            @window_gen.generate(opening, wall, storey.elevation, storey_group.entities, evidence: evidence)
          when 'door'
            @door_gen.generate(opening, wall, storey.elevation, storey_group.entities, evidence: evidence)
          end
        end

        wall_group
      end

      def opening_evidence(opening, document)
        source = opening.source.is_a?(Hash) ? opening.source : {}
        review = document.reconstruction.is_a?(Hash) ? document.reconstruction['uncertainty_review'] : nil
        decisions = review.is_a?(Hash) ? (review['decisions'] || []) : []
        decision = decisions.find do |item|
          item.is_a?(Hash) && !item['model_opening_index'].nil? && !source['opening_index'].nil? &&
            item['model_opening_index'].to_i == source['opening_index'].to_i
        end
        {
          source: source['type'] || opening.source || 'unknown',
          confidence: opening.confidence,
          decision: decision && decision['decision'],
          evidence_opening_id: decision && decision['opening_id'],
          reviewer: decision && decision['reviewer'],
          reviewed_at: decision && decision['reviewed_at']
        }
      end
    end
  end
end
