# frozen_string_literal: true

module Geomora
  module Core
    class LodPolicy
      ELEMENT_LOD = {
        'floor' => 100,
        'roof' => 100,
        'wall' => 100,
        'window' => 200,
        'door' => 200,
        'column' => 200,
        'balcony' => 200,
        'beam' => 200,
        'stair' => 200,
        'parapet' => 200,
        'cornice' => 300,
        'trim' => 300,
        'railing' => 300,
        'eaves' => 300
      }.freeze

      DEFAULT_LEVEL = 200

      class << self
        def normalize(level)
          case level
          when 100, '100', 'lod_100', :lod_100 then 100
          when 200, '200', 'lod_200', :lod_200 then 200
          when 300, '300', 'lod_300', :lod_300 then 300
          else
            DEFAULT_LEVEL
          end
        end

        def label(level)
          "LOD #{normalize(level)}"
        end

        def include_element?(type, level)
          required = ELEMENT_LOD.fetch(type.to_s, 300)
          normalize(level) >= required
        end

        def include_openings?(level)
          normalize(level) >= 200
        end

        def include_lod300_details?(level)
          normalize(level) >= 300
        end

        def elements_for_level(level)
          normalized = normalize(level)
          ELEMENT_LOD.select { |_type, min| min <= normalized }.keys
        end
      end
    end
  end
end
