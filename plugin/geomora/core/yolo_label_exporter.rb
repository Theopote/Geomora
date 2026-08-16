# frozen_string_literal: true

require 'fileutils'

module Geomora
  module Core
    class YoloLabelExporter
      WINDOW_CLASS = 0
      DOOR_CLASS = 1
      MIN_BOX_SIZE = 0.002

      ExportResult = Struct.new(
        :dataset_root,
        :split,
        :stem,
        :image_path,
        :label_path,
        :box_count,
        keyword_init: true
      )

      def self.default_dataset_root
        candidate = File.expand_path('../../backend/data/facade_yolo_custom', Project.plugin_root)
        return candidate if File.directory?(candidate)

        File.join(Project.plugin_root, 'cache', 'yolo_export')
      end

      def self.export!(
        rectified_path:,
        dataset_root:,
        split:,
        windows:,
        door_bbox: nil,
        source_path: nil,
        project_name: nil,
        stem: nil
      )
        raise GeomoraError, 'Rectified image missing.' if rectified_path.nil? || rectified_path.empty?
        raise GeomoraError, "Rectified image not found: #{rectified_path}" unless File.exist?(rectified_path)

        normalized_split = split.to_s.strip.downcase
        unless %w[train val].include?(normalized_split)
          raise GeomoraError, 'Split must be train or val.'
        end

        lines = build_lines(windows: windows, door_bbox: door_bbox)
        raise GeomoraError, 'No window or door boxes to export. Draw or detect openings first.' if lines.empty?

        root = File.expand_path(dataset_root.to_s)
        images_dir = File.join(root, normalized_split, 'images')
        labels_dir = File.join(root, normalized_split, 'labels')
        FileUtils.mkdir_p(images_dir)
        FileUtils.mkdir_p(labels_dir)

        sample_stem = stem.to_s.strip
        sample_stem = build_stem(source_path, project_name) if sample_stem.empty?
        ext = File.extname(rectified_path)
        ext = '.jpg' if ext.empty?

        image_path = File.join(images_dir, "#{sample_stem}#{ext}")
        label_path = File.join(labels_dir, "#{sample_stem}.txt")

        FileUtils.cp(rectified_path, image_path)
        File.write(label_path, lines.join("\n") + "\n", encoding: 'UTF-8')

        ExportResult.new(
          dataset_root: root,
          split: normalized_split,
          stem: sample_stem,
          image_path: image_path,
          label_path: label_path,
          box_count: lines.length
        )
      end

      def self.build_lines(windows:, door_bbox: nil)
        lines = []

        Array(windows).each do |window|
          bbox = normalize_bbox(window.is_a?(Hash) ? window['bbox_norm'] : window[:bbox_norm])
          next unless bbox

          lines << bbox_norm_to_yolo_line(WINDOW_CLASS, bbox)
        end

        door = normalize_bbox(door_bbox)
        lines << bbox_norm_to_yolo_line(DOOR_CLASS, door) if door

        lines
      end

      def self.bbox_norm_to_yolo_line(class_id, bbox)
        x1, y1, x2, y2 = bbox.map(&:to_f)
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        width = x2 - x1
        height = y2 - y1
        format('%d %.6f %.6f %.6f %.6f', class_id, cx, cy, width, height)
      end

      def self.normalize_bbox(raw)
        return nil unless raw.is_a?(Array) && raw.length == 4

        values = raw.map(&:to_f)
        return nil if values.any? { |value| value.nan? || value.infinite? }

        x1, y1, x2, y2 = values
        x1, x2 = [x1, x2].minmax
        y1, y2 = [y1, y2].minmax
        width = x2 - x1
        height = y2 - y1
        return nil if width < MIN_BOX_SIZE || height < MIN_BOX_SIZE
        return nil if x1 < 0.0 || y1 < 0.0 || x2 > 1.0 || y2 > 1.0

        [x1, y1, x2, y2]
      end

      def self.build_stem(source_path, project_name)
        base =
          if source_path && !source_path.to_s.strip.empty?
            File.basename(source_path.to_s, '.*')
          else
            project_name.to_s
          end
        base = base.gsub(/[^\w\-]+/, '_').gsub(/_+/, '_').downcase
        base = 'facade' if base.empty?
        "#{base}_#{Time.now.strftime('%Y%m%d_%H%M%S')}"
      end
      private_class_method :build_stem
    end
  end
end
