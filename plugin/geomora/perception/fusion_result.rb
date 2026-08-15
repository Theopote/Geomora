# frozen_string_literal: true

require 'json'

module Geomora
  module Perception
    class FusionResult
      attr_reader :method, :confidence, :image_width, :image_height,
                  :elements, :overlay_base64, :homography, :registration, :debug

      def self.from_hash(data)
        new(data)
      end

      def initialize(data)
        @method = data['method']
        @confidence = data['confidence'].to_f
        @image_width = data['image_width'].to_i
        @image_height = data['image_height'].to_i
        @elements = data['elements'] || []
        @overlay_base64 = data['overlay_base64']
        @homography = data['homography']
        @registration = data['registration']
        @debug = data['debug'] || {}
      end

      def to_detection_result
        DetectionResult.from_hash(
          'method' => method,
          'confidence' => confidence,
          'image_width' => image_width,
          'image_height' => image_height,
          'elements' => elements,
          'overlay_base64' => overlay_base64,
          'debug' => debug
        )
      end

      def to_dict
        {
          'method' => method,
          'confidence' => confidence,
          'image_width' => image_width,
          'image_height' => image_height,
          'element_count' => elements.length,
          'windows' => elements.count { |e| e['type'] == 'window' },
          'doors' => elements.count { |e| e['type'] == 'door' },
          'homography' => homography,
          'debug' => debug
        }
      end

      def to_source_metadata
        {
          'fusion_method' => method,
          'fusion_confidence' => confidence,
          'homography' => homography,
          'fused_elements' => elements,
          'debug' => debug
        }
      end
    end
  end
end
