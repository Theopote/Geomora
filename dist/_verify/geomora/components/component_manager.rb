# frozen_string_literal: true

module Geomora
  module Components
    class ComponentManager
      def initialize(model)
        @model = model
        @definitions = model.definitions
        @cache = {}
      end

      def find_or_create(definition_id, &block)
        if @cache[definition_id]
          Logger.debug("Reusing cached component #{definition_id}")
          return @cache[definition_id]
        end

        existing = @definitions[definition_id]
        if existing && !existing.deleted?
          Logger.debug("Reusing existing component #{definition_id}")
          @cache[definition_id] = existing
          return existing
        end

        Logger.debug("Creating component #{definition_id}")
        definition = @definitions.add(definition_id)
        yield(definition) if block
        @cache[definition_id] = definition
        definition
      end

      def cached?(definition_id)
        @cache.key?(definition_id) || !@definitions[definition_id].nil?
      end
    end
  end
end
