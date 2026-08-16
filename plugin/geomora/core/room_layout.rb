# frozen_string_literal: true

module Geomora
  module Core
    class RoomLayout
      ITEM_PATTERN = /
        (?<kind>[a-z_]+)
        @
        (?:
          (?<wall>wall_(?:north|south|east|west))
          |
          (?<x>[-\d.]+)
          ,
          (?<y>[-\d.]+)
          (?:,
          (?<width>[-\d.]+)
          x
          (?<depth>[-\d.]+)
          x
          (?<height>[-\d.]+))?
        )
        (?:@
        (?<rotation>\d+|wall_(?:north|south|east|west)))?
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
            category: default_category(match[:kind])
          }
          if match[:wall]
            item[:orientation] = match[:wall]
          else
            item[:position] = [match[:x].to_f, match[:y].to_f, 0]
          end
          if match[:width]
            item[:width] = match[:width].to_f
            item[:depth] = match[:depth].to_f
            item[:height] = match[:height].to_f
          end
          if match[:rotation]
            if match[:rotation].start_with?('wall_')
              item[:orientation] = match[:rotation]
            else
              item[:rotation] = match[:rotation].to_i
            end
          end
          item
        end
      end

      def self.serialize_item(item)
        kind = (item[:kind] || item['kind']).to_s
        width = (item[:width] || item['width']).to_f
        depth = (item[:depth] || item['depth']).to_f
        height = (item[:height] || item['height']).to_f
        rotation = item[:rotation] || item['rotation']
        orientation = item[:orientation] || item['orientation']
        position = item[:position] || item['position']
        if orientation && !position.is_a?(Array)
          base = "#{kind}@#{orientation}"
        elsif position.is_a?(Array)
          base = format('%s@%.0f,%.0f', kind, position[0].to_f, position[1].to_f)
          unless default_dimensions?(kind, width, depth, height)
            base += format(',%.0fx%.0fx%.0f', width, depth, height)
          end
        else
          base = "#{kind}@0,0"
        end
        return base if orientation
        return base unless rotation

        "#{base}@#{rotation.to_i % 360}"
      end

      def self.default_dimensions?(kind, width, depth, height)
        width == default_width(kind) &&
          depth == default_depth(kind) &&
          height == default_height(kind)
      end

      def self.normalize_item_hash(item)
        return nil unless item.is_a?(Hash)

        position = item['position'] || [item['x'], item['y'], item['z'] || 0]
        normalized = {
          kind: item['kind'].to_s,
          width: (item['width'] || default_width(item['kind'])).to_f,
          depth: (item['depth'] || default_depth(item['kind'])).to_f,
          height: (item['height'] || default_height(item['kind'])).to_f,
          category: item['category'] || default_category(item['kind'])
        }
        normalized[:position] = [position[0].to_f, position[1].to_f, position[2].to_f] if position
        normalized[:rotation] = item['rotation'].to_i if item['rotation']
        normalized[:orientation] = item['orientation'] if item['orientation']
        normalized
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
