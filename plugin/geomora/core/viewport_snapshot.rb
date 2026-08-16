# frozen_string_literal: true

module Geomora
  module Core
    class ViewportSnapshot
      DEFAULT_WIDTH = 480
      DEFAULT_HEIGHT = 320

      def self.capture(model = nil, width: DEFAULT_WIDTH, height: DEFAULT_HEIGHT)
        model ||= active_model
        raise GeomoraError, 'No active SketchUp model' unless model

        view = LodCapture.model_view(model)
        path = File.join(LodCapture.capture_cache_dir, "viewport_#{Time.now.to_i}.png")
        LodCapture.write_frame(view, path, width: width, height: height)
        {
          'width' => width,
          'height' => height,
          'path' => path,
          'data_url' => data_url(path)
        }
      end

      def self.data_url(path)
        encoded = LodCapture.encode_file(path)
        return nil unless encoded

        "data:image/png;base64,#{encoded}"
      end

      def self.active_model
        return Sketchup.active_model if defined?(Sketchup) && Sketchup.respond_to?(:active_model)

        nil
      end
    end
  end
end
