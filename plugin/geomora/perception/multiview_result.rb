# frozen_string_literal: true

require 'json'

module Geomora
  module Perception
    class MultiviewResult
      attr_reader :method, :confidence, :match_count, :inlier_count, :homography, :views, :debug

      def self.from_hash(data)
        new(data)
      end

      def initialize(data)
        @method = data['method']
        @confidence = data['confidence'].to_f
        @match_count = data['match_count'].to_i
        @inlier_count = data['inlier_count'].to_i
        @homography = data['homography']
        @views = data['views'] || []
        @debug = data['debug'] || {}
      end

      def to_dict
        {
          'method' => method,
          'confidence' => confidence,
          'match_count' => match_count,
          'inlier_count' => inlier_count,
          'homography' => homography,
          'views' => views,
          'debug' => debug
        }
      end

      def to_source_metadata
        {
          'multiview_method' => method,
          'multiview_confidence' => confidence,
          'multiview_match_count' => match_count,
          'multiview_inlier_count' => inlier_count,
          'views' => views
        }
      end
    end
  end
end
