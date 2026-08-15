# frozen_string_literal: true

module Geomora
  module Perception
    class RectificationResult
      attr_reader :rectified_image_path, :rectified_image_base64, :homography,
                    :vanishing_points, :corners_src, :corners_dst, :confidence,
                    :method, :line_count, :output_width, :output_height, :debug

      def self.from_hash(data)
        new(
          rectified_image_path: data['rectified_image_path'],
          rectified_image_base64: data['rectified_image_base64'],
          homography: data['homography'] || [],
          vanishing_points: data['vanishing_points'] || [],
          corners_src: data['corners_src'] || [],
          corners_dst: data['corners_dst'] || [],
          confidence: data['confidence'].to_f,
          method: data['method'],
          line_count: data['line_count'].to_i,
          output_width: data['output_width'].to_i,
          output_height: data['output_height'].to_i,
          debug: data['debug'] || {}
        )
      end

      def initialize(attrs)
        @rectified_image_path = attrs[:rectified_image_path]
        @rectified_image_base64 = attrs[:rectified_image_base64]
        @homography = attrs[:homography]
        @vanishing_points = attrs[:vanishing_points]
        @corners_src = attrs[:corners_src]
        @corners_dst = attrs[:corners_dst]
        @confidence = attrs[:confidence]
        @method = attrs[:method]
        @line_count = attrs[:line_count]
        @output_width = attrs[:output_width]
        @output_height = attrs[:output_height]
        @debug = attrs[:debug]
      end

      def to_source_metadata(original_path)
        {
          'original_path' => original_path,
          'rectified_path' => rectified_image_path,
          'homography' => homography,
          'vanishing_points' => vanishing_points,
          'corners_src' => corners_src,
          'rectification_confidence' => confidence,
          'method' => method,
          'line_count' => line_count
        }.compact
      end

      def to_dict
        {
          'rectified_image_path' => rectified_image_path,
          'confidence' => confidence,
          'method' => method,
          'line_count' => line_count,
          'output_width' => output_width,
          'output_height' => output_height,
          'vanishing_points' => vanishing_points,
          'corners_src' => corners_src
        }
      end
    end
  end
end
