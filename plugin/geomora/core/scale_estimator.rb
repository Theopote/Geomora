# frozen_string_literal: true

module Geomora
  module Core
    class ScaleEstimator
      STANDARD_DOOR_HEIGHT_MM = 2100.0
      STANDARD_SILL_HEIGHT_MM = 900.0
      FACADE_MARGIN_FACTOR = 0.88

      def self.apply_hint!(params, scale_hint)
        return params unless scale_hint.is_a?(Hash)

        length = scale_hint['wall_length_mm']
        height = scale_hint['wall_height_mm']
        return params if length.to_f <= 0 || height.to_f <= 0

        params['wall_length'] = length.to_f.round
        params['wall_height'] = height.to_f.round
        params['scale_hint'] = scale_hint
        params
      end

      def self.from_detection(elements, image_width:, image_height:, facade_bounds: nil)
        return nil if elements.nil? || elements.empty?

        doors = elements.select { |element| element['type'] == 'door' }
        windows = elements.select { |element| element['type'] == 'window' }

        wall_height = estimate_wall_height(doors, windows)
        return nil unless wall_height

        wall_length = estimate_wall_length(
          elements,
          wall_height,
          image_width,
          image_height,
          window_count: windows.length,
          facade_bounds: facade_bounds
        )
        return nil unless wall_length

        {
          'wall_length_mm' => wall_length.round,
          'wall_height_mm' => wall_height.round,
          'method' => 'ruby_fallback',
          'confidence' => 0.5
        }
      end

      def self.estimate_wall_height(doors, windows)
        if doors.any?
          door = doors.max_by { |element| element['confidence'].to_f }
          bbox = door['bbox_norm']
          door_height_norm = bbox[3].to_f - bbox[1].to_f
          return snap_mm(STANDARD_DOOR_HEIGHT_MM / door_height_norm, 50.0) if door_height_norm >= 0.08
        end

        return nil if windows.empty?

        window = windows.max_by { |element| element['confidence'].to_f }
        bbox = window['bbox_norm']
        sill_norm = [1.0 - bbox[3].to_f, 0.05].max
        snap_mm(STANDARD_SILL_HEIGHT_MM / sill_norm, 50.0)
      end

      def self.estimate_wall_length(
        elements,
        wall_height,
        image_width,
        image_height,
        window_count: nil,
        facade_bounds: nil
      )
        return nil if image_width.to_i <= 0 || image_height.to_i <= 0

        x_min = elements.map { |element| element['bbox_norm'][0].to_f }.min
        x_max = elements.map { |element| element['bbox_norm'][2].to_f }.max
        span_norm = [x_max - x_min, 0.25].max
        span_norm = extrapolate_span_norm(
          span_norm,
          window_count: window_count || elements.count { |element| element['type'] == 'window' },
          facade_bounds: facade_bounds,
          image_width: image_width
        )

        aspect = image_width.to_f / image_height.to_f
        length = (span_norm * wall_height * aspect) / FACADE_MARGIN_FACTOR
        snap_mm(length.clamp(4000.0, 30_000.0), 100.0)
      end

      def self.extrapolate_span_norm(span_norm, window_count:, facade_bounds:, image_width:)
        adjusted = span_norm

        if facade_bounds.is_a?(Array) && facade_bounds.length >= 4 && image_width.to_i.positive?
          facade_span = (facade_bounds[2].to_f - facade_bounds[0].to_f) / image_width.to_f
          adjusted = [adjusted, facade_span * 0.85].max
        end

        if window_count <= 2
          adjusted = [adjusted, 0.72].max
        elsif window_count <= 4
          adjusted = [adjusted, 0.58].max
        end

        [adjusted, 0.98].min
      end

      def self.snap_mm(value, grid)
        ((value / grid).round * grid).round(1)
      end
    end
  end
end
