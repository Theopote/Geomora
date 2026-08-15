# frozen_string_literal: true

module Geomora
  module Core
    class PatternAnalyzer
      PITCH_TOLERANCE_MM = 25.0
      SIZE_TOLERANCE_MM = 5.0

      def self.analyze(params)
        new(params).analyze
      end

      def initialize(params)
        @params = params.is_a?(Hash) ? params : {}
      end

      def analyze
        windows = normalize_windows(@params['windows'])
        door = @params['door']
        wall_length = float_param('wall_length', 10_000)

        if windows.length < 2
          return result(windows, door, pattern_type: 'none', patterns_detected: [])
        end

        sorted = windows.sort_by { |win| win['offset'].to_f }
        translation = translation_row?(sorted)
        pitch = bay_pitch(sorted)
        grid = !pitch.nil?
        mirror = mirror_symmetry?(sorted, wall_length, door)

        patterns_detected = []
        patterns_detected << 'translation' if translation
        patterns_detected << 'grid' if grid
        patterns_detected << 'mirror' if mirror
        patterns_detected << 'window_bay' if translation && grid

        pattern_type = derive_type(patterns_detected)
        component_id = component_id_for(sorted.first) if translation

        enriched = sorted.each_with_index.map do |win, index|
          entry = win.merge('pattern_index' => index)
          entry['component_id'] = component_id if component_id
          entry
        end

        result(
          enriched,
          door,
          pattern_type: pattern_type,
          patterns_detected: patterns_detected,
          bay_count: sorted.length,
          bay_pitch: pitch,
          component_id: component_id,
          mirror_axis: mirror ? wall_length / 2.0 : nil
        )
      end

      private

      def normalize_windows(raw)
        return [] unless raw.is_a?(Array)

        raw.map do |win|
          next unless win.is_a?(Hash)

          {
            'offset' => win['offset'].to_f,
            'width' => win['width'].to_f,
            'height' => win['height'].to_f,
            'sill_height' => win['sill_height'].to_f,
            'confidence' => win['confidence'],
            'bbox_norm' => win['bbox_norm'],
            'pattern_index' => win['pattern_index'],
            'component_id' => win['component_id']
          }.compact
        end.compact
      end

      def float_param(key, default)
        value = @params[key]
        value.nil? ? default : value.to_f
      end

      def translation_row?(windows)
        widths = windows.map { |win| win['width'].to_f }
        heights = windows.map { |win| win['height'].to_f }
        sills = windows.map { |win| win['sill_height'].to_f }

        close?(widths) && close?(heights) && close?(sills)
      end

      def bay_pitch(windows)
        return nil if windows.length < 2

        pitches = (0...(windows.length - 1)).map do |index|
          windows[index + 1]['offset'].to_f - windows[index]['offset'].to_f
        end
        return nil unless close?(pitches)

        pitches.first.round(1)
      end

      def mirror_symmetry?(windows, wall_length, door)
        return false unless door.nil? || door['width'].to_f <= 0

        centers = windows.map { |win| win['offset'].to_f + (win['width'].to_f / 2.0) }
        axis = wall_length / 2.0
        mirrored = centers.reverse.map { |center| (2 * axis) - center }
        centers.each_with_index.all? { |center, index| (center - mirrored[index]).abs <= PITCH_TOLERANCE_MM }
      end

      def derive_type(patterns_detected)
        return 'none' if patterns_detected.empty?
        return 'translation_grid' if patterns_detected.include?('window_bay')
        return 'translation_row' if patterns_detected.include?('translation')
        return 'mirror_row' if patterns_detected.include?('mirror')

        'custom'
      end

      def component_id_for(window)
        width = window['width'].to_i
        height = window['height'].to_i
        "window_bay_#{width}x#{height}"
      end

      def close?(values)
        return false if values.empty?

        reference = values.first.to_f
        values.all? { |value| (value.to_f - reference).abs <= SIZE_TOLERANCE_MM }
      end

      def result(windows, door, pattern_type:, patterns_detected:, bay_count: 0, bay_pitch: nil,
                 component_id: nil, mirror_axis: nil)
        {
          'windows' => windows,
          'door' => door || empty_door,
          'pattern' => {
            'method' => 'facade_bay_v1',
            'type' => pattern_type,
            'patterns_detected' => patterns_detected,
            'bay_count' => bay_count,
            'bay_pitch' => bay_pitch,
            'component_id' => component_id,
            'mirror_axis' => mirror_axis,
            'shared_component' => !component_id.nil?
          }
        }
      end

      def empty_door
        {
          'offset' => 0,
          'width' => 0,
          'height' => 0,
          'confidence' => 0.0
        }
      end
    end
  end
end
