# frozen_string_literal: true

module Geomora
  module Tags
    TAGS = %w[
      Geomora_Walls
      Geomora_Windows
      Geomora_Doors
      Geomora_Roofs
      Geomora_Reference
    ].freeze

    class Manager
      def initialize(model)
        @model = model
        @cache = {}
      end

      def apply(entity, tag_name)
        entity.layer = find_or_create(tag_name)
      end

      def find_or_create(tag_name)
        @cache[tag_name] ||= @model.layers[tag_name] || @model.layers.add(tag_name)
      end
    end
  end
end
