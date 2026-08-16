# frozen_string_literal: true

module Geomora
  module Tags
    TAGS = %w[
      Geomora_Walls
      Geomora_InteriorWalls
      Geomora_Windows
      Geomora_Doors
      Geomora_Floors
      Geomora_Roofs
      Geomora_Columns
      Geomora_Beams
      Geomora_Stairs
      Geomora_Balconies
      Geomora_Parapets
      Geomora_Cornices
      Geomora_Trim
      Geomora_Railings
      Geomora_Eaves
      Geomora_Rooms
      Geomora_Furniture
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
