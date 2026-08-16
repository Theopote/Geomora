# frozen_string_literal: true

module Geomora
  module Core
    class RoomLayout
      ITEM_PATTERN = /
        (?<kind>[a-z_]+)
        @
        (?<x>[-\d.]+)
        ,
        (?<y>[-\d.]+)
        (?:,
        (?<width>[-\d.]+)
        x
        (?<depth>[-\d.]+)
        x
        (?<height>[-\d.]+))?
      /ix

      def self.enabled?(params)
        raw = params['room_furniture_layouts'] || params[:room_furniture_layouts]
        !raw.nil? && !raw.to_s.strip.empty?
      end

      def self.items_for_room(room_number:, room_id:, params:, storey_index: 0)
        layouts = parse(params, storey_index: storey_index)
        layouts[room_number] || layouts[room_id.to_s] || []
      end

      def self.parse(params, storey_index: 0)
        raw = params['room_furniture_layouts'] || params[:room_furniture_layouts]
        return {} if raw.nil? || raw.to_s.strip.empty?

        if raw.is_a?(Hash)
          storey_key = format('storey_%02d', storey_index + 1)
          scoped = raw[storey_key] || raw[storey_index.to_s] || raw
          return parse_room_map(scoped)
        end

        parse_string(raw.to_s, storey_index: storey_index)
      end

      def self.parse_string(value, storey_index: 0)
        map = {}
        value.split(';').each do |segment|
          token = segment.strip
          next if token.empty?

          if (match = token.match(/\As(?<storey>\d+):(?<rest>.+)\z/i))
            next unless match[:storey].to_i == storey_index + 1

            token = match[:rest]
          end

          room_token, items_token = token.split(':', 2)
          next if room_token.nil? || items_token.nil?

          room_key = room_token.strip
          next if room_key.empty?

          items = parse_items(items_token)
          next if items.empty?

          key = room_key.match?(/\A\d+\z/) ? room_key.to_i : room_key
          map[key] = items
        end
        map
      end

      def self.parse_room_map(value)
        return {} unless value.is_a?(Hash)

        value.each_with_object({}) do |(room_key, items_token), map|
          items = if items_token.is_a?(Array)
                    items_token.map { |item| normalize_item_hash(item) }.compact
                  else
                    parse_items(items_token.to_s)
                  end
          next if items.empty?

          key = room_key.to_s.match?(/\A\d+\z/) ? room_key.to_i : room_key.to_s
          map[key] = items
        end
      end

      def self.parse_items(value)
        value.split('|').filter_map do |entry|
          match = entry.strip.match(ITEM_PATTERN)
          next unless match

          item = {
            kind: match[:kind].downcase,
            width: default_width(match[:kind]),
            depth: default_depth(match[:kind]),
            height: default_height(match[:kind]),
            position: [match[:x].to_f, match[:y].to_f, 0],
            category: default_category(match[:kind])
          }
          if match[:width]
            item[:width] = match[:width].to_f
            item[:depth] = match[:depth].to_f
            item[:height] = match[:height].to_f
          end
          item
        end
      end

      def self.normalize_item_hash(item)
        return nil unless item.is_a?(Hash)

        position = item['position'] || [item['x'], item['y'], item['z'] || 0]
        {
          kind: item['kind'].to_s,
          width: (item['width'] || default_width(item['kind'])).to_f,
          depth: (item['depth'] || default_depth(item['kind'])).to_f,
          height: (item['height'] || default_height(item['kind'])).to_f,
          position: [position[0].to_f, position[1].to_f, position[2].to_f],
          category: item['category'] || default_category(item['kind'])
        }
      end

      def self.default_width(kind)
        FixtureLibrary::SETS.values.flatten.find { |item| item[:kind] == kind.to_s }&.dig(:width) || 1200
      end

      def self.default_depth(kind)
        FixtureLibrary::SETS.values.flatten.find { |item| item[:kind] == kind.to_s }&.dig(:depth) || 800
      end

      def self.default_height(kind)
        FixtureLibrary::SETS.values.flatten.find { |item| item[:kind] == kind.to_s }&.dig(:height) || 750
      end

      def self.default_category(kind)
        %w[sink stove fridge toilet shower bathtub vanity].include?(kind.to_s) ? 'fixture' : 'furniture'
      end
    end
  end
end
