# frozen_string_literal: true

module Geomora
  module Core
    class FurniturePlanner
      CATALOG = {
        'living' => { kind: 'sofa', width: 2000, depth: 900, height: 800 },
        'bedroom' => { kind: 'bed', width: 2000, depth: 1500, height: 500 },
        'bathroom' => { kind: 'vanity', width: 800, depth: 500, height: 850 },
        'kitchen' => { kind: 'counter', width: 1800, depth: 600, height: 900 },
        'study' => { kind: 'desk', width: 1400, depth: 700, height: 750 },
        'corridor' => { kind: 'bench', width: 1200, depth: 400, height: 450 },
        'generic' => { kind: 'table', width: 1200, depth: 800, height: 750 }
      }.freeze

      def self.enabled?(params)
        config = params['building_elements'] || params[:building_elements]
        return false unless config.is_a?(Hash)

        value = config['furniture'] || config[:furniture]
        value == true || value.to_s == 'true'
      end

      def self.plan(rooms:, params:, storey_index: 0)
        return [] unless enabled?(params)
        return [] if rooms.empty?
        return [] unless LodPolicy.include_element?(:furniture, lod_level(params))

        suffix = format('%02d', storey_index + 1)
        rooms.flat_map.with_index do |room, index|
          plan_for_room(room, suffix: suffix, index: index + 1)
        end
      end

      def self.plan_for_room(room, suffix:, index:)
        room_type = room.dig('semantic', 'room_type') || 'generic'
        spec = CATALOG[room_type] || CATALOG['generic']
        polygon = room.dig('geometry', 'polygon')
        return [] unless polygon.is_a?(Array) && polygon.length >= 3

        bounds = room_bounds(polygon)
        position = placement_position(bounds, spec)
        return [] unless position

        [
          {
            'id' => format('furniture_%s_%02d_%s', suffix, index, spec[:kind]),
            'type' => 'furniture',
            'storey_id' => room['storey_id'],
            'room_id' => room['id'],
            'geometry' => {
              'position' => position,
              'width' => spec[:width],
              'depth' => spec[:depth],
              'height' => spec[:height]
            },
            'semantic' => {
              'kind' => spec[:kind],
              'room_type' => room_type
            },
            'confidence' => 1.0
          }
        ]
      end

      def self.room_bounds(polygon)
        xs = polygon.map { |point| point[0].to_f }
        ys = polygon.map { |point| point[1].to_f }
        {
          x_min: xs.min,
          x_max: xs.max,
          y_min: ys.min,
          y_max: ys.max
        }
      end

      def self.placement_position(bounds, spec)
        inset = 600.0
        x = bounds[:x_min] + inset
        y = bounds[:y_min] + inset
        return nil if x + spec[:width] > bounds[:x_max] - inset
        return nil if y + spec[:depth] > bounds[:y_max] - inset

        [x, y, 0]
      end

      def self.lod_level(params)
        LodPolicy.normalize(params['lod_level'] || params[:lod_level])
      end
    end
  end
end
