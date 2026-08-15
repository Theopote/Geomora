# frozen_string_literal: true

module Geomora
  module Core
    class Rationalizer
    DEFAULT_GRID_MM = 50.0
    MIN_OPENING_WIDTH_MM = 300.0
    MIN_GAP_MM = 50.0
    MIN_MARGIN_MM = 50.0

    def self.rationalize(params, grid_mm: DEFAULT_GRID_MM)
      new(params, grid_mm: grid_mm).rationalize
    end

    def initialize(params, grid_mm: DEFAULT_GRID_MM)
      @params = params.is_a?(Hash) ? params : {}
      @grid_mm = grid_mm.to_f
      @grid_mm = DEFAULT_GRID_MM if @grid_mm <= 0
    end

    def rationalize
      windows = normalize_windows(@params['windows'])
      door = normalize_door(@params['door'])
      wall_length = float_param('wall_length', 10_000)
      wall_height = float_param('wall_height', 3300)

      return empty_result(windows, door) if windows.empty?

      windows = apply_equal_dimensions(windows)
      door = rationalize_door(door, wall_height) if door_active?(door)
      windows = layout_equal_spacing(windows, wall_length, door)

      {
        'windows' => windows,
        'door' => door,
        'rationalization' => {
          'method' => 'facade_row_v1',
          'grid_mm' => @grid_mm,
          'constraints_applied' => constraints_applied(windows, door)
        }
      }
    end

    private

    def empty_result(windows, door)
      {
        'windows' => windows,
        'door' => door,
        'rationalization' => {
          'method' => 'facade_row_v1',
          'grid_mm' => @grid_mm,
          'constraints_applied' => []
        }
      }
    end

    def float_param(key, default)
      value = @params[key]
      value.nil? ? default : value.to_f
    end

    def normalize_windows(raw)
      return [] unless raw.is_a?(Array)

      raw.map do |win|
        next unless win.is_a?(Hash)

        {
          'offset' => snap(win['offset']),
          'width' => snap(win['width']),
          'height' => snap(win['height']),
          'sill_height' => snap(win['sill_height']),
          'confidence' => win['confidence'],
          'bbox_norm' => win['bbox_norm']
        }.compact
      end.compact
    end

    def normalize_door(raw)
      return empty_door unless raw.is_a?(Hash)

      {
        'offset' => snap(raw['offset']),
        'width' => snap(raw['width']),
        'height' => snap(raw['height']),
        'confidence' => raw['confidence'],
        'bbox_norm' => raw['bbox_norm']
      }.compact
    end

    def apply_equal_dimensions(windows)
      width = snap(median(windows.map { |win| win['width'].to_f }))
      height = snap(median(windows.map { |win| win['height'].to_f }))
      sill = snap(median(windows.map { |win| win['sill_height'].to_f }))

      width = [width, MIN_OPENING_WIDTH_MM].max
      height = [height, MIN_OPENING_WIDTH_MM].max
      sill = [sill, 0].max

      windows.map do |win|
        win.merge(
          'width' => width,
          'height' => height,
          'sill_height' => sill
        )
      end
    end

    def rationalize_door(door, wall_height)
      width = [snap(door['width'].to_f), MIN_OPENING_WIDTH_MM].max
      height = [[snap(door['height'].to_f), MIN_OPENING_WIDTH_MM].max, wall_height].min
      offset = [[snap(door['offset'].to_f), 0].max, float_param('wall_length', 10_000) - width].min

      door.merge(
        'offset' => offset,
        'width' => width,
        'height' => height
      )
    end

    def layout_equal_spacing(windows, wall_length, door)
      count = windows.length
      return windows if count.zero?

      width = windows.first['width'].to_f
      zone = window_zone(wall_length, door, width)
      return windows unless zone

      zone_start, zone_end = zone
      zone_width = zone_end - zone_start
      total_windows = count * width
      return windows if zone_width <= total_windows

      spacing = (zone_width - total_windows) / (count + 1.0)
      spacing = [snap(spacing), MIN_GAP_MM].max

      used = total_windows + spacing * (count + 1)
      if used > zone_width
        spacing = [(zone_width - total_windows) / (count + 1.0), MIN_GAP_MM].max
      end

      zone_start += (zone_width - total_windows - spacing * (count + 1)) / 2.0
      zone_start = snap(zone_start)

      windows.each_with_index.map do |win, index|
        offset = zone_start + spacing + index * (width + spacing)
        win.merge('offset' => snap(offset))
      end
    end

    def window_zone(wall_length, door, window_width)
      return [MIN_MARGIN_MM, wall_length - MIN_MARGIN_MM] unless door_active?(door)

      door_offset = door['offset'].to_f
      door_width = door['width'].to_f
      door_end = door_offset + door_width

      if door_on_left?(door_offset, door_width, wall_length)
        start = door_end + MIN_GAP_MM
        finish = wall_length - MIN_MARGIN_MM
      else
        start = MIN_MARGIN_MM
        finish = door_offset - MIN_GAP_MM
      end

      return nil if finish - start < window_width + MIN_GAP_MM

      [start, finish]
    end

    def door_on_left?(offset, width, wall_length)
      center = offset + (width / 2.0)
      center <= wall_length / 2.0
    end

    def door_active?(door)
      door.is_a?(Hash) && door['width'].to_f > 0
    end

    def constraints_applied(windows, door)
      applied = %w[snap_grid]
      applied << 'equal_width' if windows.length >= 2
      applied << 'equal_height' if windows.length >= 2
      applied << 'align' if windows.length >= 2
      applied << 'equal_spacing' if windows.length >= 2
      applied << 'symmetry' if windows.length >= 2
      applied << 'fixed_dimension' if door_active?(door)
      applied
    end

    def median(values)
      sorted = values.map(&:to_f).sort
      return 0.0 if sorted.empty?

      mid = sorted.length / 2
      if sorted.length.odd?
        sorted[mid]
      else
        (sorted[mid - 1] + sorted[mid]) / 2.0
      end
    end

    def snap(value)
      ((value.to_f / @grid_mm).round * @grid_mm).round(1)
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
