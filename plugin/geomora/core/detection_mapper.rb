# frozen_string_literal: true

module Geomora
  module Core
    class DetectionMapper
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
