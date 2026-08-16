# frozen_string_literal: true

module Geomora
  module Core
    class LodPresentation
      def self.geomora_pages(model)
        return [] unless model.respond_to?(:pages)

        names = LodScenePages.page_names
        LodScenes::PRESETS.values.map do |level|
          LodScenePages.find_page(model, LodScenePages.page_name_for(level))
        end.compact
      end

      def self.next_scene(model)
        pages = geomora_pages(model)
        raise GeomoraError, 'No Geomora LOD scenes found. Create LOD Scene Pages first.' if pages.empty?

        current = model.pages.selected_page
        current_index = pages.index(current)
        next_index = current_index.nil? ? 0 : (current_index + 1) % pages.length
        page = pages[next_index]
        model.pages.selected_page = page
        level = level_from_page_name(page.name)
        LodVisibility.apply(model, level) if level
        page.name
      end

      def self.tour_manifest(model)
        geomora_pages(model).map.with_index do |page, index|
          {
            'order' => index + 1,
            'name' => page.name,
            'lod_level' => level_from_page_name(page.name)
          }
        end
      end

      def self.export_tour_json(model)
        tour_manifest(model).to_json
      end

      def self.level_from_page_name(name)
        match = name.to_s.match(/LOD\s+(\d+)/)
        return nil unless match

        match[1].to_i
      end
    end
  end
end
