# frozen_string_literal: true

module Geomora
  module Perception
    class DetectionResult
      attr_reader :method, :confidence, :image_width, :image_height,
                    :elements, :overlay_base64, :debug

      def self.from_hash(data)
        new(
          method: data['method'],
          confidence: data['confidence'].to_f,
          image_width: data['image_width'].to_i,
          image_height: data['image_height'].to_i,
          elements: data['elements'] || [],
          overlay_base64: data['overlay_base64'],
          debug: data['debug'] || {}
        )
      end

      def initialize(attrs)
        @method = attrs[:method]
        @confidence = attrs[:confidence]
        @image_width = attrs[:image_width]
        @image_height = attrs[:image_height]
        @elements = attrs[:elements]
        @overlay_base64 = attrs[:overlay_base64]
        @debug = attrs[:debug]
      end

      def to_dict
        {
          'method' => method,
          'confidence' => confidence,
          'image_width' => image_width,
          'image_height' => image_height,
          'element_count' => elements.length,
          'windows' => elements.count { |e| e['type'] == 'window' },
          'doors' => elements.count { |e| e['type'] == 'door' }
        }
      end

      def to_source_metadata
        {
          'detection_method' => method,
          'detection_confidence' => confidence,
          'detected_elements' => elements
        }
      end
    end
  end
end
