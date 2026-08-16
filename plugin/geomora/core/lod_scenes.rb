# frozen_string_literal: true

module Geomora
  module Core
    class LodScenes
      PRESETS = {
        lod_100: 100,
        lod_200: 200,
        lod_300: 300
      }.freeze

      class << self
        def preset_names
          PRESETS.keys
        end

        def apply_preset(model, preset)
          level = PRESETS.fetch(preset.to_sym) do
            raise GeomoraError, "Unknown LOD preset: #{preset}"
          end

          apply_level(model, level)
        end

        def apply_level(model, level)
          LodVisibility.apply(model, level)
          LodPolicy.label(level)
        end
      end
    end
  end
end
