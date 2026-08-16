# frozen_string_literal: true

require 'json'

module Geomora
  module Core
    class RoomClassifier
      TYPE_LABELS = {
        'living' => 'Living Room',
        'bedroom' => 'Bedroom',
        'bathroom' => 'Bathroom',
        'kitchen' => 'Kitchen',
        'study' => 'Study',
        'corridor' => 'Corridor',
        'generic' => 'Room'
      }.freeze

      def self.enabled?(params)
        config = params['building_elements'] || params[:building_elements]
        return true unless config.is_a?(Hash)

        value = config['room_types'] || config[:room_types]
        value != false && value.to_s != 'false'
      end

      def self.classify(rooms, params:, storey_index: 0)
        return rooms if rooms.empty?
        return rooms unless enabled?(params)

        classified = rooms.map { |room| deep_dup_room(room) }
        assign_types(classified, storey_index: storey_index)
        classified
      end

      def self.assign_types(rooms, storey_index: 0)
        total = rooms.length
        areas = rooms.map { |room| room.dig('semantic', 'area_mm2').to_f }
        largest_index = areas.each_with_index.max_by { |area, _| area }&.last || 0
        smallest_index = areas.each_with_index.min_by { |area, _| area }&.last || 0

        rooms.each_with_index do |room, index|
          room_type = infer_type(
            index: index,
            total: total,
            largest_index: largest_index,
            smallest_index: smallest_index,
            storey_index: storey_index,
            area: areas[index]
          )
          room['semantic']['room_type'] = room_type
          room['name'] = if total == 1
                           TYPE_LABELS[room_type]
                         else
                           format('%s %d', TYPE_LABELS[room_type], index + 1)
                         end
        end
      end

      def self.infer_type(index:, total:, largest_index:, smallest_index:, storey_index:, area:)
        return 'living' if total == 1
        return 'living' if index.zero? && storey_index.zero?
        return 'bathroom' if total >= 3 && index == smallest_index && area < largest_room_area_threshold(total)
        return 'bedroom' if index == largest_index && index != smallest_index
        return 'study' if total == 2 && index == 1
        return 'corridor' if total >= 3 && narrow_room?(area, total)

        'bedroom'
      end

      def self.largest_room_area_threshold(total)
        total >= 4 ? 8_000_000.0 : 6_000_000.0
      end

      def self.narrow_room?(area, total)
        return false if total < 3

        area < 5_000_000.0
      end

      def self.deep_dup_room(room)
        JSON.parse(JSON.generate(room))
      end
    end
  end
end
