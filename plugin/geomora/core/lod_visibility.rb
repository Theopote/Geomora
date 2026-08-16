# frozen_string_literal: true

module Geomora
  module Core
    class LodVisibility
      TAG_MIN_LOD = {
        'Geomora_Reference' => 100,
        'Geomora_Walls' => 100,
        'Geomora_Floors' => 100,
        'Geomora_Roofs' => 100,
        'Geomora_InteriorWalls' => 200,
        'Geomora_Windows' => 200,
        'Geomora_Doors' => 200,
        'Geomora_Columns' => 200,
        'Geomora_Beams' => 200,
        'Geomora_Stairs' => 200,
        'Geomora_Balconies' => 200,
        'Geomora_Parapets' => 200,
        'Geomora_Cornices' => 300,
        'Geomora_Trim' => 300,
        'Geomora_Railings' => 300,
        'Geomora_Eaves' => 300,
        'Geomora_Rooms' => 200,
        'Geomora_Furniture' => 300,
        'Geomora_Fixtures' => 300
      }.freeze

      class << self
        def hidden_tags_for(level)
          normalized = LodPolicy.normalize(level)
          TAG_MIN_LOD.select { |_tag, min_lod| min_lod > normalized }.keys
        end

        def visible_tags_for(level)
          normalized = LodPolicy.normalize(level)
          TAG_MIN_LOD.select { |_tag, min_lod| min_lod <= normalized }.keys
        end

        def apply(model, level)
          return unless model.respond_to?(:layers)

          normalized = LodPolicy.normalize(level)
          TAG_MIN_LOD.each do |tag_name, min_lod|
            layer = model.layers[tag_name]
            next unless layer

            layer.visible = min_lod <= normalized
          end

          Logger.info("LOD visibility applied: #{LodPolicy.label(normalized)}")
        end
      end
    end
  end
end
