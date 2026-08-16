# frozen_string_literal: true

module Geomora
  module Core
    class IRBuilder
      def self.build_manual_facade(params)
        new(params).build
      end

      def initialize(params)
        @params = params.is_a?(Hash) ? params : {}
      end

      def build
        storey_payloads = build_storey_payloads
        storeys = storey_payloads.map { |payload| payload[:storey] }
        openings = storey_payloads.flat_map { |payload| payload[:openings] }
        rooms = storey_payloads.flat_map { |payload| payload[:rooms] }
        furniture = storey_payloads.flat_map { |payload| payload[:furniture] }
        windows = openings.select { |opening| opening['type'] == 'window' }
        doors = openings.select { |opening| opening['type'] == 'door' }

        ir = {
          'schema_version' => Geomora::SCHEMA_VERSION,
          'project' => {
            'id' => 'project_001',
            'name' => @params.fetch('project_name', 'Manual Facade'),
            'unit' => 'mm',
            'coordinate_system' => 'z_up',
            'default_wall_thickness' => wall_thickness,
            'lod_level' => lod_level
          },
          'buildings' => [
            {
              'id' => 'building_001',
              'name' => 'Main Building',
              'storeys' => storeys
            }
          ],
          'openings' => openings,
          'components' => build_components(windows, doors),
          'constraints' => build_constraints(windows),
          'sources' => build_sources
        }
        ir['rooms'] = rooms unless rooms.empty?
        ir['furniture'] = furniture unless furniture.empty?
        ir
      end

      private

      def build_storey_payloads
        elevations = storey_elevations
        payloads = []

        storey_count.times do |index|
          payloads << build_storey_payload(index, elevations[index])
        end

        payloads
      end

      def build_storey_payload(index, elevation)
        storey_id = format('storey_%02d', index + 1)
        height = storey_height
        facade_wall_id = format('wall_%02d_01', index + 1)
        walls, openings = build_storey_walls(
          storey_id: storey_id,
          storey_index: index,
          facade_wall_id: facade_wall_id,
          height: height
        )
        building_elements = Core::BuildingComposer.compose(
          @params,
          wall_length: wall_length,
          wall_height: height,
          wall_thickness: wall_thickness,
          storey_id: storey_id,
          storey_index: index,
          top_storey: index == storey_count - 1
        )

        rooms = build_storey_rooms(storey_id: storey_id, storey_index: index)
        furniture = Core::FurniturePlanner.plan(
          rooms: rooms,
          params: @params,
          storey_index: index
        )

        {
          storey: {
            'id' => storey_id,
            'name' => storey_name(index),
            'elevation' => elevation,
            'height' => height,
            'elements' => walls + building_elements
          },
          openings: openings,
          rooms: rooms,
          furniture: furniture
        }
      end

      def build_storey_walls(storey_id:, storey_index:, facade_wall_id:, height:)
        openings = []
        opening_ids = []

        if LodPolicy.include_openings?(lod_level) && should_build_windows?(storey_index)
          windows = build_windows(facade_wall_id, storey_index)
          openings.concat(windows)
          opening_ids.concat(windows.map { |window| window['id'] })
        end

        if storey_index.zero? && LodPolicy.include_openings?(lod_level)
          door = build_door(facade_wall_id)
          if door
            openings << door
            opening_ids << door['id']
          end
        end

        walls = if perimeter_walls_enabled?
                  perimeter = Core::WallEnclosure.perimeter_walls(
                    wall_length: wall_length,
                    wall_thickness: wall_thickness,
                    building_depth: building_depth,
                    storey_id: storey_id,
                    storey_index: storey_index,
                    wall_height: height,
                    facade_wall_id: facade_wall_id,
                    facade_semantic: facade_semantic_with_openings(opening_ids)
                  )
                  perimeter[0]['opening_ids'] = opening_ids
                  perimeter
                else
                  [
                    {
                      'id' => facade_wall_id,
                      'type' => 'wall',
                      'storey_id' => storey_id,
                      'geometry' => {
                        'baseline' => [[0, 0, 0], [wall_length, 0, 0]],
                        'height' => height,
                        'thickness' => wall_thickness
                      },
                      'semantic' => { 'exterior' => true },
                      'opening_ids' => opening_ids,
                      'confidence' => 1.0
                    }
                  ]
                end

        partition_walls, partition_openings = interior_partition_data(
          storey_id: storey_id,
          storey_index: storey_index,
          height: height
        )
        walls.concat(partition_walls)
        openings.concat(partition_openings)

        [walls, openings]
      end

      def facade_semantic_with_openings(opening_ids)
        semantic = { 'exterior' => true, 'join_group' => 'perimeter', 'join_role' => 'facade' }
        semantic['opening_ids'] = opening_ids unless opening_ids.empty?
        semantic
      end

      def storey_elevations
        elevations = []
        storey_count.times do |index|
          elevations << index * storey_height
        end
        elevations
      end

      def storey_name(index)
        index.zero? ? 'Ground Floor' : format('Floor %d', index + 1)
      end

      def storey_count
        count = int_param('storey_count', 1)
        count < 1 ? 1 : count
      end

      def storey_height
        value = @params['storey_height']
        value.nil? ? wall_height : value.to_f
      end

      def building_depth
        float_param('building_depth', 6000)
      end

      def perimeter_walls_enabled?
        Core::WallEnclosure.enabled?(@params)
      end

      def interior_partition_data(storey_id:, storey_index:, height:)
        return [[], []] unless Core::InteriorLayout.enabled?(@params)

        walls = Core::InteriorLayout.partition_walls(
          params: @params,
          wall_length: wall_length,
          wall_thickness: wall_thickness,
          building_depth: building_depth,
          storey_id: storey_id,
          storey_index: storey_index,
          wall_height: height,
          perimeter_walls: perimeter_walls_enabled?
        )
        result = if LodPolicy.include_openings?(lod_level)
                   Core::InteriorLayout.partition_openings(
                     walls: walls,
                     params: @params,
                     wall_thickness: wall_thickness,
                     wall_height: height,
                     storey_index: storey_index
                   )
                 else
                   { walls: walls, openings: [] }
                 end
        [result[:walls], result[:openings]]
      end

      def build_storey_rooms(storey_id:, storey_index:)
        rooms = Core::RoomPlanner.plan(
          params: @params,
          wall_length: wall_length,
          building_depth: building_depth,
          storey_id: storey_id,
          storey_index: storey_index,
          perimeter_walls: perimeter_walls_enabled?
        )
        Core::RoomClassifier.classify(
          rooms,
          params: @params,
          storey_index: storey_index
        )
      end

      def lod_level
        LodPolicy.normalize(@params['lod_level'])
      end

      def repeat_openings_for_storey?(index)
        index.zero? || repeat_openings?
      end

      def should_build_windows?(storey_index)
        if storey_index.positive? && !repeat_openings? && independent_storey_windows?
          return windows_for_storey(storey_index).any?
        end

        storey_index.zero? || repeat_openings?
      end

      def independent_storey_windows?
        storey_windows = @params['storey_windows']
        storey_windows.is_a?(Array) && storey_windows.length > 1 && !repeat_openings?
      end

      def windows_for_storey(storey_index)
        storey_windows = @params['storey_windows']
        if storey_windows.is_a?(Array) && storey_windows[storey_index].is_a?(Array)
          return storey_windows[storey_index]
        end

        if storey_index.zero?
          raw = @params['windows']
          return raw.is_a?(Array) ? raw : []
        end

        return windows_for_storey(0) if repeat_openings?

        []
      end

      def repeat_openings?
        option_enabled('repeat_openings', true)
      end

      def option_enabled(key, default)
        value = @params[key]
        return default if value.nil?

        value == true || value.to_s == 'true' || value == 'on' || value == 1 || value == '1'
      end

      def wall_length
        float_param('wall_length', 10_000)
      end

      def wall_height
        float_param('wall_height', 3300)
      end

      def wall_thickness
        float_param('wall_thickness', 240)
      end

      def float_param(key, default)
        value = @params[key]
        value.nil? ? default : value.to_f
      end

      def int_param(key, default)
        value = @params[key]
        value.nil? ? default : value.to_i
      end

      def build_windows(wall_id, storey_index)
        raw = windows_for_storey(storey_index)
        return [] unless raw.is_a?(Array)
        return [] if raw.empty?

        raw.each_with_index.map do |win, index|
          width = (win['width'] || 1500).to_f
          height = (win['height'] || 1500).to_f
          {
            'id' => format('window_%02d_%02d', storey_index + 1, index + 1),
            'type' => 'window',
            'parent_id' => wall_id,
            'geometry' => {
              'offset' => (win['offset'] || 0).to_f,
              'sill_height' => (win['sill_height'] || 900).to_f,
              'width' => width,
              'height' => height,
              'depth' => wall_thickness
            },
            'component' => {
              'definition_id' => window_definition_id(win, width, height)
            },
            'confidence' => win['confidence'] || 1.0
          }
        end
      end

      def window_definition_id(win, width, height)
        pattern = @params['pattern']
        if pattern.is_a?(Hash) && pattern['component_id'] && !pattern['component_id'].to_s.empty?
          return pattern['component_id']
        end
        if win['component_id'] && !win['component_id'].to_s.empty?
          return win['component_id']
        end

        "window_standard_#{width.to_i}"
      end

      def build_door(wall_id)
        door = @params['door']
        return nil unless door.is_a?(Hash)

        width = (door['width'] || 0).to_f
        return nil if width <= 0

        {
          'id' => 'door_001',
          'type' => 'door',
          'parent_id' => wall_id,
          'geometry' => {
            'offset' => (door['offset'] || 0).to_f,
            'width' => width,
            'height' => (door['height'] || 2100).to_f,
            'depth' => wall_thickness
          },
          'component' => {
            'definition_id' => door_component_id({ 'width' => width, 'height' => (door['height'] || 2100).to_f })
          },
          'confidence' => 1.0
        }
      end

      def build_components(windows, doors)
        defs = {}

        windows.each do |win|
          def_id = win.dig('component', 'definition_id')
          next if defs.key?(def_id)

          defs[def_id] = {
            'id' => def_id,
            'type' => 'window',
            'parameters' => {
              'width' => win.dig('geometry', 'width'),
              'height' => win.dig('geometry', 'height')
            }
          }
        end

        door_list = doors.is_a?(Array) ? doors : [doors]
        door_list.compact.each do |door|
          door_def = door.dig('component', 'definition_id')
          next if door_def.nil? || door_def.to_s.empty?
          next if defs.key?(door_def)

          defs[door_def] = {
            'id' => door_def,
            'type' => 'door',
            'parameters' => {
              'width' => door.dig('geometry', 'width'),
              'height' => door.dig('geometry', 'height')
            }
          }
        end

        defs.values
      end

      def build_constraints(windows)
        return [] if windows.length < 2

        window_ids = windows.map { |w| w['id'] }
        rationalization = @params['rationalization']
        applied = rationalization.is_a?(Hash) ? rationalization['constraints_applied'] : nil
        applied = %w[equal_width equal_height equal_spacing align symmetry] if applied.nil? || applied.empty?

        constraints = []
        if applied.include?('equal_width')
          constraints << constraint_entry('constraint_equal_width', 'equal_width', window_ids)
        end
        if applied.include?('equal_height')
          constraints << constraint_entry('constraint_equal_height', 'equal_height', window_ids)
        end
        if applied.include?('equal_spacing') && window_ids.length >= 2
          constraints << constraint_entry('constraint_equal_spacing', 'equal_spacing', window_ids)
        end
        if applied.include?('align')
          constraints << constraint_entry('constraint_align', 'align', window_ids)
        end
        if applied.include?('symmetry')
          constraints << constraint_entry('constraint_symmetry', 'symmetry', window_ids)
        end
        constraints.concat(pattern_constraints(windows))

        constraints
      end

      def pattern_constraints(windows)
        pattern = @params['pattern']
        return [] unless pattern.is_a?(Hash)

        constraints = []
        window_ids = windows.map { |w| w['id'] }
        detected = pattern['patterns_detected']
        detected = [] unless detected.is_a?(Array)

        if detected.include?('grid') && pattern['bay_pitch']
          constraints << {
            'id' => 'constraint_grid',
            'type' => 'grid',
            'targets' => window_ids,
            'priority' => 'hard',
            'parameters' => {
              'pitch' => pattern['bay_pitch'],
              'bay_count' => pattern['bay_count']
            }
          }
        end

        if detected.include?('mirror') && pattern['mirror_axis']
          constraints << {
            'id' => 'constraint_mirror',
            'type' => 'symmetry',
            'targets' => window_ids,
            'priority' => 'soft',
            'parameters' => {
              'axis' => 'vertical',
              'position' => pattern['mirror_axis']
            }
          }
        end

        constraints
      end

      def door_component_id(door)
        pattern = @params['pattern']
        width = door['width'].to_i
        if pattern.is_a?(Hash) && pattern['door_component_id'] && !pattern['door_component_id'].to_s.empty?
          return pattern['door_component_id']
        end

        "door_standard_#{width}"
      end

      def constraint_entry(id, type, targets)
        {
          'id' => id,
          'type' => type,
          'targets' => targets,
          'priority' => 'hard'
        }
      end

      def build_sources
        sources = []
        source_id = @params['source_id']
        return sources if source_id.nil? || source_id.to_s.empty?

        metadata = { 'path' => @params['source_path'], 'role' => 'primary' }
        metadata.merge!(view_metadata(@params['rectification'])) if @params['rectification'].is_a?(Hash)
        metadata.merge!(view_metadata(@params['detection'])) if @params['detection'].is_a?(Hash)
        metadata['rationalization'] = @params['rationalization'] if @params['rationalization'].is_a?(Hash)
        metadata['pattern'] = @params['pattern'] if @params['pattern'].is_a?(Hash)
        metadata['multiview'] = @params['multiview'] if @params['multiview'].is_a?(Hash)
        metadata['fusion'] = @params['fusion'] if @params['fusion'].is_a?(Hash)

        sources << {
          'id' => source_id.to_s,
          'type' => 'image',
          'metadata' => metadata.compact
        }

        secondary_path = @params['secondary_source_path']
        if secondary_path && !secondary_path.to_s.empty?
          secondary_meta = { 'path' => secondary_path, 'role' => 'secondary' }
          if @params['multiview'].is_a?(Hash)
            view = (@params['multiview']['views'] || []).find { |item| item['role'] == 'secondary' }
            secondary_meta['transform_to_primary'] = view['transform_to_primary'] if view
          end
          sources << {
            'id' => 'view_002',
            'type' => 'image',
            'metadata' => secondary_meta.compact
          }
        end

        sources
      end

      def view_metadata(data)
        data.is_a?(Hash) ? data : {}
      end
    end
  end
end
