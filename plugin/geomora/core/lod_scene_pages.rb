# frozen_string_literal: true

module Geomora
  module Core
    class LodScenePages
      PAGE_FLAGS = if defined?(::PAGE_USE_LAYER_VISIBILITY)
                     ::PAGE_USE_LAYER_VISIBILITY
                   elsif defined?(Sketchup::Page) && Sketchup::Page.const_defined?(:PAGE_USE_LAYER_VISIBILITY)
                     Sketchup::Page::PAGE_USE_LAYER_VISIBILITY
                   else
                     64
                   end

      def self.page_names
        LodScenes::PRESETS.map { |_preset, level| page_name_for(level) }
      end

      def self.page_name_for(level)
        "Geomora #{LodPolicy.label(level)}"
      end

      def self.create_pages(model)
        raise GeomoraError, 'SketchUp model pages are unavailable.' unless model.respond_to?(:pages)

        model.start_operation('Geomora Create LOD Scenes', true)
        created = []

        LodScenes::PRESETS.each_value do |level|
          name = page_name_for(level)
          page = find_page(model, name) || model.pages.add(name)
          LodVisibility.apply(model, level)
          page.update(PAGE_FLAGS)
          created << name
        end

        model.pages.selected_page = find_page(model, page_name_for(200)) if model.pages.length.positive?
        model.commit_operation
        Logger.info("LOD scene pages created: #{created.join(', ')}")
        created
      end

      def self.find_page(model, name)
        model.pages.find { |page| page.name == name }
      end
    end
  end
end
