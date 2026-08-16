# frozen_string_literal: true

module Geomora
  module Core
    class InteriorLayout
      def self.enabled?(params)
        config = params['building_elements'] || params[:building_elements]
        return false unless config.is_a?(Hash)

        value = config['interior_partitions'] || config[:interior_partitions]
        value == true || value.to_s == 'true'
      end

      def self.partition_walls(
        params:,
        wall_length:,
        wall_thickness:,
        building_depth:,
        storey_id:,
        storey_index:,
        wall_height:,
        perimeter_walls: false
      )
        count = partition_count(params)
        return [] if count < 1

        y_range = interior_y_range(building_depth, wall_thickness, perimeter_walls)
        suffix = format('%02d', storey_index + 1)
        thickness = partition_thickness(params, wall_thickness)

        (1..count).map do |index|
          x = wall_length * index / (count + 1.0)
          {
            'id' => format('partition_%s_%02d', suffix, index),
            'type' => 'wall',
            'storey_id' => storey_id,
            'geometry' => {
              'baseline' => [[x, y_range[:start], 0], [x, y_range[:end], 0]],
              'height' => wall_height,
              'thickness' => thickness
            },
            'semantic' => {
              'interior' => true,
              'partition' => true,
              'partition_index' => index
            },
            'opening_ids' => [],
            'confidence' => 1.0
          }
        end
      end

      def self.partition_count(params)
        value = params['partition_count'] || params[:partition_count]
        count = value.nil? ? 1 : value.to_i
        count < 1 ? 0 : count
      end

      def self.partition_thickness(params, default)
        value = params['partition_thickness'] || params[:partition_thickness]
        value.nil? ? default : value.to_f
      end

      def self.partition_doors_enabled?(params)
        config = params['building_elements'] || params[:building_elements]
        return false unless config.is_a?(Hash)

        value = config['partition_doors'] || config[:partition_doors]
        value == true || value.to_s == 'true'
      end

      def self.partition_openings(walls:, params:, wall_thickness:, wall_height:, storey_index:)
        return { walls: walls, openings: [] } unless partition_doors_enabled?(params)

        openings = []
        door_width = partition_door_width(params)
        door_height = partition_door_height(params, wall_height)
        suffix = format('%02d', storey_index + 1)

        walls.each do |wall|
          next unless partition_wall?(wall)

          baseline = wall.dig('geometry', 'baseline')
          next unless baseline.is_a?(Array) && baseline.length == 2

          wall_run = wall_run_length(baseline)
          next if wall_run <= door_width

          partition_index = wall.dig('semantic', 'partition_index') || 1
          offset = partition_door_offset(params, wall_run, door_width, partition_index: partition_index)
          opening_id = format('partition_door_%s_%02d', suffix, wall['semantic']['partition_index'])
          openings << {
            'id' => opening_id,
            'type' => 'door',
            'parent_id' => wall['id'],
            'geometry' => {
              'offset' => offset,
              'sill_height' => 0,
              'width' => door_width,
              'height' => door_height,
              'depth' => wall_thickness
            },
            'component' => {
              'definition_id' => partition_door_component_id(door_width, door_height)
            },
            'semantic' => { 'interior' => true, 'partition_door' => true },
            'confidence' => 1.0
          }
          wall['opening_ids'] = [opening_id]
        end

        { walls: walls, openings: openings }
      end

      def self.partition_wall?(wall)
        semantic = wall['semantic']
        semantic.is_a?(Hash) && semantic['partition'] == true
      end

      def self.wall_run_length(baseline)
        dx = baseline[1][0].to_f - baseline[0][0].to_f
        dy = baseline[1][1].to_f - baseline[0][1].to_f
        Math.sqrt((dx * dx) + (dy * dy))
      end

      def self.partition_door_width(params)
        value = params['partition_door_width'] || params[:partition_door_width]
        value.nil? ? 900.0 : value.to_f
      end

      def self.partition_door_height(params, wall_height)
        value = params['partition_door_height'] || params[:partition_door_height]
        height = value.nil? ? 2100.0 : value.to_f
        [height, wall_height].min
      end

      def self.partition_door_offset(params, wall_run, door_width, partition_index: 1)
        offsets = params['partition_door_offsets'] || params[:partition_door_offsets]
        value = if offsets.is_a?(Array) && !offsets[partition_index - 1].nil?
                  offsets[partition_index - 1]
                else
                  params['partition_door_offset'] || params[:partition_door_offset]
                end
        return (wall_run - door_width) / 2.0 if value.nil?

        offset = value.to_f
        [[offset, 0].max, wall_run - door_width].min
      end

      def self.partition_door_component_id(width, height)
        format('door_partition_%dx%d', width.to_i, height.to_i)
      end

      def self.interior_y_range(building_depth, wall_thickness, perimeter_walls)
        if perimeter_walls
          half_depth = building_depth / 2.0
          half_thickness = wall_thickness / 2.0
          {
            start: half_thickness,
            end: half_depth - half_thickness
          }
        else
          inset = wall_thickness / 2.0
          {
            start: inset,
            end: building_depth - inset
          }
        end
      end
    end
  end
end
