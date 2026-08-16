# frozen_string_literal: true

module Geomora
  module Core
    class RoomLayoutEditor
      def self.preview(params, storey_index: 0)
        wall_length = (params['wall_length'] || params[:wall_length] || 10_000).to_f
        building_depth = (params['building_depth'] || params[:building_depth] || 6000).to_f
        perimeter = perimeter_walls?(params)
        thickness = RoomPlanner.send(:partition_thickness, params)
        y_range = InteriorLayout.interior_y_range(building_depth, thickness, perimeter)
        x_bounds = RoomPlanner.partition_x_bounds(params, wall_length)

        (0...(x_bounds.length - 1)).map.with_index do |index, room_index|
          bound = {
            x_min: x_bounds[index],
            x_max: x_bounds[index + 1],
            y_min: y_range[:start],
            y_max: y_range[:end]
          }
          room_number = room_index + 1
          room_id = format('room_%02d_%02d', storey_index + 1, room_number)
          items = RoomLayout.items_for_room(
            room_number: room_number,
            room_id: room_id,
            params: params,
            storey_index: storey_index
          )
          if items.empty?
            preset = RoomLayoutPresets::PRESETS[
              RoomLayoutPresets.inferred_type(room_number, x_bounds.length - 1, storey_index: storey_index)
            ]
            items = RoomLayout.parse_items(preset) if preset
          end

          {
            'room_number' => room_number,
            'room_id' => room_id,
            'name' => RoomPlanner.send(:room_name, room_index, x_bounds.length - 1),
            'bounds' => bound,
            'items' => items.map { |item| preview_item(item) }
          }
        end
      end

      def self.preview_item(item)
        position = item[:position] || [600.0, 600.0, 0]
        {
          'kind' => item[:kind].to_s,
          'width' => item[:width].to_f,
          'depth' => item[:depth].to_f,
          'height' => item[:height].to_f,
          'position' => [position[0].to_f, position[1].to_f, position[2].to_f],
          'rotation' => item[:rotation],
          'orientation' => item[:orientation]
        }.compact
      end

      def self.serialize_layout(params, rooms_payload, storey_index: 0)
        prefix = storey_index.positive? ? format('s%d:', storey_index + 1) : ''
        rooms_payload.map do |room|
          items = (room['items'] || []).map { |item| RoomLayout.serialize_item(item) }.join('|')
          format('%s%d:%s', prefix, room['room_number'], items)
        end.join(';')
      end

      def self.perimeter_walls?(params)
        config = params['building_elements'] || params[:building_elements]
        return false unless config.is_a?(Hash)

        value = config['perimeter_walls'] || config[:perimeter_walls]
        value == true || value.to_s == 'true'
      end
    end
  end
end
