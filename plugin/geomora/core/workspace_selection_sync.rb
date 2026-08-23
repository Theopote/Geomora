# frozen_string_literal: true

require 'json'
require_relative '../metadata/attributes'
require_relative 'logger'

module Geomora
  module Core
    SelectionObserverBase = defined?(Sketchup::SelectionObserver) ? Sketchup::SelectionObserver : Object

    class WorkspaceSelectionObserver < SelectionObserverBase
      def initialize(callback)
        @callback = callback
      end

      def onSelectionBulkChange(selection)
        @callback.call(selection)
      end

      def onSelectionAdded(selection, _entity)
        @callback.call(selection)
      end

      def onSelectionCleared(selection)
        @callback.call(selection)
      end
    end

    class WorkspaceSelectionSync
      EVIDENCE_KEYS = %w[
        entity_id entity_type ai_source ai_confidence review_decision
        evidence_opening_id reviewed_by reviewed_at
      ].freeze

      class << self
        def start(dialog, model: sketchup_model)
          stop
          return false unless model && model.respond_to?(:selection)

          @dialog = dialog
          @selection = model.selection
          @observer = WorkspaceSelectionObserver.new(method(:selection_changed))
          @selection.add_observer(@observer)
          selection_changed(@selection)
          true
        end

        def stop
          @selection.remove_observer(@observer) if @selection && @observer && @selection.respond_to?(:remove_observer)
          @selection = @observer = @dialog = nil
        rescue StandardError
          @selection = @observer = @dialog = nil
        end

        def select_entity(entity_id, model: sketchup_model)
          return false if entity_id.to_s.empty? || model.nil?

          entity = find_entity(model.entities, entity_id.to_s)
          return false unless entity

          model.selection.clear
          model.selection.add(entity)
          true
        rescue StandardError => error
          Logger.warn("Workspace model selection failed: #{error.message}")
          false
        end

        private

        def sketchup_model
          defined?(Sketchup) && Sketchup.respond_to?(:active_model) ? Sketchup.active_model : nil
        end

        def selection_changed(selection)
          entity = selection.to_a.reverse.find { |item| Metadata::Attributes.geomora_entity?(item) }
          payload = entity ? EVIDENCE_KEYS.to_h { |key| [key, Metadata::Attributes.read(entity, key)] }.compact : nil
          @dialog&.execute_script("window.geomora.setModelSelection(#{payload.to_json})")
        rescue StandardError => error
          Logger.warn("Workspace selection sync failed: #{error.message}")
        end

        def find_entity(entities, entity_id)
          entities.each do |entity|
            return entity if Metadata::Attributes.read(entity, 'entity_id') == entity_id

            nested = if entity.respond_to?(:entities)
                       entity.entities
                     elsif entity.respond_to?(:definition) && entity.definition.respond_to?(:entities)
                       entity.definition.entities
                     end
            found = find_entity(nested, entity_id) if nested
            return found if found
          end
          nil
        end
      end
    end
  end
end
