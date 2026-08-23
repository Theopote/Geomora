# frozen_string_literal: true

require 'json'

module Geomora
  module Core
    module Settings
      SECTION = 'Geomora'
      KEY = 'ai_settings_v1'
      DEFAULTS = {
        'routing_mode' => 'automatic',
        'vlm_provider' => 'openai',
        'vlm_model' => 'auto',
        'detection_method' => 'auto',
        'depth_method' => 'auto',
        'onnx_device' => 'auto',
        'cloud_upload_confirm' => true,
        'cache_vlm_evidence' => true,
        'require_review_before_generate' => true,
        'log_level' => 'info'
      }.freeze
      ENUMS = {
        'routing_mode' => %w[automatic local_only cloud_enhanced],
        'vlm_provider' => %w[openai gemini],
        'detection_method' => %w[auto sam_v1 facade_row_v1 yolo_v1 contour_v1],
        'depth_method' => %w[auto colmap_dense_v1 depth_anything_v2_small_v1 depth_anything_v2_small_q4_v1 marigold_v1_1_v1 midas_v21_v1 gradient_laplacian_v1],
        'onnx_device' => %w[auto cpu cuda directml],
        'log_level' => %w[error warning info debug]
      }.freeze
      BOOLEAN_KEYS = %w[cloud_upload_confirm cache_vlm_evidence require_review_before_generate].freeze

      module_function

      def load
        raw = Sketchup.read_default(SECTION, KEY, '{}')
        sanitize(JSON.parse(raw.to_s))
      rescue JSON::ParserError
        DEFAULTS.dup
      end

      def save(value)
        clean = sanitize(value)
        Sketchup.write_default(SECTION, KEY, JSON.generate(clean))
        clean
      end

      def sanitize(value)
        input = value.is_a?(Hash) ? value : {}
        clean = DEFAULTS.dup
        ENUMS.each do |key, allowed|
          candidate = input[key].to_s
          clean[key] = candidate if allowed.include?(candidate)
        end
        BOOLEAN_KEYS.each { |key| clean[key] = !!input[key] if input.key?(key) }
        model = input['vlm_model'].to_s.strip
        clean['vlm_model'] = model[0, 100] unless model.empty?
        clean
      end
    end
  end
end
