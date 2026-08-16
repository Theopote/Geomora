# frozen_string_literal: true

module Geomora
  module Core
    class RoomLayoutPresets
      PRESETS = {
        'living' => 'sofa@600,600|coffee_table@1200,600',
        'bedroom' => 'bed@600,600|wardrobe@600,2200',
        'kitchen' => 'counter@600,600|sink@1000,600|stove@1800,600',
        'bathroom' => 'vanity@600,600|toilet@600,2200|shower@2200,2200',
        'study' => 'desk@600,600|bookshelf@600,2200',
        'generic' => 'table@600,600'
      }.freeze

      def self.suggest(params, storey_index: 0)
        count = InteriorLayout.partition_count(params)
        room_count = count + 1
        prefix = storey_index.positive? ? format('s%d:', storey_index + 1) : ''
        segments = []

        room_count.times do |index|
          room_number = index + 1
          room_type = inferred_type(room_number, room_count, storey_index: storey_index)
          preset = PRESETS[room_type] || PRESETS['generic']
          segments << format('%s%d:%s', prefix, room_number, preset)
        end

        segments.join(';')
      end

      def self.inferred_type(room_number, room_count, storey_index: 0)
        return 'living' if room_count == 1
        return 'living' if room_number == 1 && storey_index.zero?
        return 'bathroom' if room_count >= 3 && room_number == room_count
        return 'study' if room_count == 2 && room_number == 2

        'bedroom'
      end
    end
  end
end
