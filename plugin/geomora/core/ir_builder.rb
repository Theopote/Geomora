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
        wall_id = 'wall_001'
        storey_id = 'storey_01'
        windows = build_windows(wall_id)
        door = build_door(wall_id)
        opening_ids = windows.map { |w| w['id'] }
        opening_ids << door['id'] if door
        openings = windows + (door ? [door] : [])

        {
          'schema_version' => Geomora::SCHEMA_VERSION,
          'project' => {
            'id' => 'project_001',
            'name' => @params.fetch('project_name', 'Manual Facade'),
            'unit' => 'mm',
            'coordinate_system' => 'z_up',
            'default_wall_thickness' => wall_thickness
          },
          'buildings' => [
            {
              'id' => 'building_001',
              'name' => 'Main Building',
              'storeys' => [
                {
                  'id' => storey_id,
                  'name' => 'Ground Floor',
                  'elevation' => 0,
                  'height' => wall_height,
                  'elements' => [
                    {
                      'id' => wall_id,
                      'type' => 'wall',
                      'storey_id' => storey_id,
                      'geometry' => {
                        'baseline' => [[0, 0, 0], [wall_length, 0, 0]],
                        'height' => wall_height,
                        'thickness' => wall_thickness
                      },
                      'semantic' => { 'exterior' => true },
                      'opening_ids' => opening_ids,
                      'confidence' => 1.0
                    }
                  ]
                }
              ]
            }
          ],
          'openings' => openings,
          'components' => build_components(windows, door),
          'constraints' => build_constraints(windows),
          'sources' => build_sources
        }
      end

      private

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

      def build_windows(wall_id)
        raw = @params['windows']
        return [] unless raw.is_a?(Array)
        return [] if raw.empty?

        raw.each_with_index.map do |win, index|
          width = (win['width'] || 1500).to_f
          height = (win['height'] || 1500).to_f
          {
            'id' => format('window_%03d', index + 1),
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
              'definition_id' => "window_standard_#{width.to_i}"
            },
            'confidence' => 1.0
          }
        end
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
            'definition_id' => "door_standard_#{width.to_i}"
          },
          'confidence' => 1.0
        }
      end

      def build_components(windows, door)
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

        if door
          door_def = door.dig('component', 'definition_id')
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

        [
          {
            'id' => 'constraint_001',
            'type' => 'equal_width',
            'targets' => windows.map { |w| w['id'] },
            'priority' => 'hard'
          }
        ]
      end

      def build_sources
        sources = []
        source_id = @params['source_id']
        return sources if source_id.nil? || source_id.to_s.empty?

        metadata = { 'path' => @params['source_path'] }
        if @params['rectification'].is_a?(Hash)
          metadata.merge!(@params['rectification'])
        end
        if @params['detection'].is_a?(Hash)
          metadata.merge!(@params['detection'])
        end

        sources << {
          'id' => source_id.to_s,
          'type' => 'image',
          'metadata' => metadata.compact
        }
        sources
      end

      def default_windows
        [
          { 'offset' => 500, 'width' => 1500, 'height' => 1500, 'sill_height' => 900 },
          { 'offset' => 2500, 'width' => 1500, 'height' => 1500, 'sill_height' => 900 },
          { 'offset' => 4500, 'width' => 1500, 'height' => 1500, 'sill_height' => 900 },
          { 'offset' => 6500, 'width' => 1500, 'height' => 1500, 'sill_height' => 900 }
        ]
      end

      def default_door
        { 'offset' => 8500, 'width' => 900, 'height' => 2100 }
      end
    end
  end
end
