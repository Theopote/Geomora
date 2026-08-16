# frozen_string_literal: true

module Geomora
  module Core
    class RoomOverrides
      VALID_TYPES = RoomClassifier::TYPE_LABELS.keys.freeze

      def self.apply(rooms, params:, storey_index: 0)
        return rooms if rooms.empty?

        overrides = parse(params, storey_index: storey_index)
        return rooms if overrides.empty?

        rooms.map.with_index do |room, index|
          room_number = index + 1
          room_id = room['id']
          type = overrides[room_number] || overrides[room_id.to_s]
          next room unless type

          apply_type(
            RoomClassifier.send(:deep_dup_room, room),
            type,
            room_number: room_number,
            total: rooms.length
          )
        end
      end

      def self.apply_type(room, type, room_number:, total:)
        normalized = type.to_s
        return room unless VALID_TYPES.include?(normalized)

        room['semantic']['room_type'] = normalized
        room['semantic']['override'] = true
        label = RoomClassifier::TYPE_LABELS[normalized]
        room['name'] = total == 1 ? label : format('%s %d', label, room_number)
        room
      end

      def self.parse(params, storey_index: 0)
        raw = params['room_type_overrides'] || params[:room_type_overrides]
        storey_key = format('storey_%02d', storey_index + 1)
        if raw.is_a?(Hash)
          scoped = raw[storey_key] || raw[storey_index.to_s] || raw
          return normalize_map(scoped)
        end
        return {} if raw.nil? || raw.to_s.strip.empty?

        normalize_string(filter_storey_entries(raw.to_s, storey_index: storey_index))
      end

      def self.filter_storey_entries(value, storey_index:)
        value.split(',').filter_map do |entry|
          token = entry.strip
          next if token.empty?

          if (match = token.match(/\As(?<storey>\d+):(?<rest>.+)\z/i))
            next unless match[:storey].to_i == storey_index + 1

            match[:rest]
          else
            token
          end
        end.join(',')
      end

      def self.normalize_string(value)
        map = {}
        value.split(',').each do |entry|
          token = entry.strip
          next if token.empty?

          key, type = token.split(/[:=]/, 2).map(&:strip)
          next if key.nil? || type.nil? || key.empty? || type.empty?

          map[key.to_i] = type if key.match?(/\A\d+\z/)
          map[key] = type
        end
        map
      end

      def self.normalize_map(value)
        return {} unless value.is_a?(Hash)

        value.each_with_object({}) do |(key, type), map|
          next if type.nil? || type.to_s.empty?

          map[key.to_i] = type.to_s if key.to_s.match?(/\A\d+\z/)
          map[key.to_s] = type.to_s
        end
      end
    end
  end
end
