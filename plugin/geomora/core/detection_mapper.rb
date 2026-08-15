# frozen_string_literal: true

module Geomora
  module Core
    class DetectionMapper
      MIN_GAP_MM = 50.0
      MIN_OPENING_WIDTH_MM = 300.0

      def self.to_facade_params(detection, wall_length:, wall_height:, wall_thickness: 240)
        new(detection, wall_length: wall_length, wall_height: wall_height, wall_thickness: wall_thickness).to_params
      end

      def initialize(detection, wall_length:, wall_height:, wall_thickness: 240)
        @detection = detection
        @wall_length = wall_length.to_f
        @wall_height = wall_height.to_f
        @wall_thickness = wall_thickness.to_f
      end

      def to_params
        windows = []
        door = nil

        @detection.elements.each do |element|
          mapped = map_element(element)
          case element['type']
          when 'window'
            windows << mapped
          when 'door'
            door = mapped if door.nil? || mapped[:confidence] > door[:confidence]
          end
        end

        windows = dedupe_overlapping_windows(windows)
        windows = trim_horizontal_gaps(windows)
        windows.sort_by! { |item| item[:offset] }

        {
          'windows' => windows.map { |item| stringify(item) },
          'door' => stringify(door || default_door)
        }
      end

      private

      def map_element(element)
        bbox = element['bbox_norm']
        raise GeomoraError, 'Detection element missing bbox_norm' unless bbox.is_a?(Array) && bbox.length == 4

        x_min, y_min, x_max, y_max = bbox.map(&:to_f)
        inset = 0.01
        x_min = [[x_min + inset, 0.0].max, 1.0].min
        y_min = [[y_min + inset, 0.0].max, 1.0].min
        x_max = [[x_max - inset, 0.0].max, 1.0].min
        y_max = [[y_max - inset, 0.0].max, 1.0].min

        width = (x_max - x_min) * @wall_length
        height = (y_max - y_min) * @wall_height
        offset = x_min * @wall_length
        sill_height = (1.0 - y_max) * @wall_height

        {
          offset: offset.round(1),
          width: width.round(1),
          height: height.round(1),
          sill_height: sill_height.round(1),
          confidence: element['confidence'].to_f
        }
      end

      def dedupe_overlapping_windows(windows)
        kept = []
        windows.sort_by { |item| -item[:confidence] }.each do |candidate|
          duplicate = kept.any? { |existing| windows_overlap?(existing, candidate) }
          kept << candidate unless duplicate
        end
        kept
      end

      def windows_overlap?(a, b)
        horizontal = a[:offset] < (b[:offset] + b[:width]) && b[:offset] < (a[:offset] + a[:width])
        return false unless horizontal

        a_bottom = a[:sill_height]
        a_top = a_bottom + a[:height]
        b_bottom = b[:sill_height]
        b_top = b_bottom + b[:height]
        a_bottom < b_top && b_bottom < a_top
      end

      def trim_horizontal_gaps(windows)
        sorted = windows.sort_by { |item| item[:offset] }
        (0...(sorted.length - 1)).each do |index|
          current = sorted[index]
          nxt = sorted[index + 1]
          current_end = current[:offset] + current[:width]
          required_start = current_end + MIN_GAP_MM
          next if nxt[:offset] >= required_start

          overlap = required_start - nxt[:offset]
          if current[:width] >= nxt[:width]
            current[:width] = [current[:width] - overlap, MIN_OPENING_WIDTH_MM].max
          else
            nxt[:offset] += overlap
            nxt[:width] = [nxt[:width] - overlap, MIN_OPENING_WIDTH_MM].max
          end
        end
        sorted
      end

      def stringify(hash)
        {
          'offset' => hash[:offset],
          'width' => hash[:width],
          'height' => hash[:height],
          'sill_height' => hash.fetch(:sill_height, 0),
          'confidence' => hash[:confidence]
        }.compact
      end

      def default_door
        {
          offset: (@wall_length * 0.75).round(1),
          width: 900.0,
          height: 2100.0,
          confidence: 0.0
        }
      end
    end
  end
end
