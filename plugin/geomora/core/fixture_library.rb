# frozen_string_literal: true

module Geomora
  module Core
    class FixtureLibrary
      SETS = {
        'living' => [
          { kind: 'sofa', width: 2000, depth: 900, height: 800, anchor: 'front_left' },
          { kind: 'coffee_table', width: 1000, depth: 600, height: 400, anchor: 'front_centre' }
        ],
        'bedroom' => [
          { kind: 'bed', width: 2000, depth: 1500, height: 500, anchor: 'front_left' },
          { kind: 'wardrobe', width: 1800, depth: 600, height: 2200, anchor: 'back_left' }
        ],
        'kitchen' => [
          { kind: 'counter', width: 2400, depth: 600, height: 900, anchor: 'front_left' },
          { kind: 'sink', width: 500, depth: 450, height: 150, anchor: 'front_left', category: 'fixture', offset: [400, 0] },
          { kind: 'stove', width: 600, depth: 600, height: 900, anchor: 'front_left', category: 'fixture', offset: [1200, 0] },
          { kind: 'fridge', width: 700, depth: 700, height: 1800, anchor: 'back_left', category: 'fixture' }
        ],
        'bathroom' => [
          { kind: 'vanity', width: 800, depth: 500, height: 850, anchor: 'front_left' },
          { kind: 'toilet', width: 400, depth: 650, height: 400, anchor: 'back_left', category: 'fixture' },
          { kind: 'shower', width: 900, depth: 900, height: 2100, anchor: 'back_right', category: 'fixture' }
        ],
        'study' => [
          { kind: 'desk', width: 1400, depth: 700, height: 750, anchor: 'front_left' },
          { kind: 'bookshelf', width: 900, depth: 350, height: 1800, anchor: 'back_left' }
        ],
        'corridor' => [
          { kind: 'bench', width: 1200, depth: 400, height: 450, anchor: 'front_centre' }
        ],
        'generic' => [
          { kind: 'table', width: 1200, depth: 800, height: 750, anchor: 'front_left' }
        ]
      }.freeze

      def self.use_sets?(params)
        config = params['building_elements'] || params[:building_elements]
        return false unless config.is_a?(Hash)
        return false unless FurniturePlanner.enabled?(params)

        value = config['fixture_sets'] || config[:fixture_sets]
        return false if value.nil?

        value == true || value.to_s == 'true'
      end

      def self.items_for(room_type, params = nil)
        base = (SETS[room_type.to_s] || SETS['generic']).dup
        return base unless params.is_a?(Hash) && FixtureCatalog.enabled?(params)

        base + FixtureCatalog.items_for(room_type, params)
      end

      def self.place_item(bounds, spec)
        inset = 600.0
        width = spec[:width].to_f
        depth = spec[:depth].to_f
        base = anchor_position(bounds, spec[:anchor], width, depth, inset)
        return nil unless base

        offset = spec[:offset] || [0, 0]
        x = base[0] + offset[0].to_f
        y = base[1] + offset[1].to_f
        return nil if x + width > bounds[:x_max] - inset
        return nil if y + depth > bounds[:y_max] - inset
        return nil if x < bounds[:x_min] + inset
        return nil if y < bounds[:y_min] + inset

        [x, y, 0]
      end

      def self.anchor_position(bounds, anchor, width, depth, inset)
        case anchor.to_s
        when 'front_right'
          [bounds[:x_max] - inset - width, bounds[:y_min] + inset]
        when 'front_centre'
          [bounds[:x_min] + ((bounds[:x_max] - bounds[:x_min] - width) / 2.0), bounds[:y_min] + inset]
        when 'back_left'
          [bounds[:x_min] + inset, bounds[:y_max] - inset - depth]
        when 'back_right'
          [bounds[:x_max] - inset - width, bounds[:y_max] - inset - depth]
        when 'back_centre'
          [bounds[:x_min] + ((bounds[:x_max] - bounds[:x_min] - width) / 2.0), bounds[:y_max] - inset - depth]
        else
          [bounds[:x_min] + inset, bounds[:y_min] + inset]
        end
      end
    end
  end
end
