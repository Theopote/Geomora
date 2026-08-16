# frozen_string_literal: true

require 'fileutils'
require 'base64'

module Geomora
  module Core
    class LodCapture
      DEFAULT_WIDTH = 960
      DEFAULT_HEIGHT = 640

      def self.capture_pages(model, width: DEFAULT_WIDTH, height: DEFAULT_HEIGHT)
        pages = LodPresentation.geomora_pages(model)
        raise GeomoraError, 'No Geomora LOD scenes found. Create LOD Scene Pages first.' if pages.empty?

        view = model_view(model)
        cache_dir = capture_cache_dir
        pages.map.with_index do |page, index|
          LodPresentation.activate_page(model, page)
          refresh_view(view)
          frame_path = File.join(cache_dir, format('lod_frame_%03d.png', index + 1))
          write_frame(view, frame_path, width: width, height: height)
          {
            'order' => index + 1,
            'name' => page.name,
            'lod_level' => LodPresentation.level_from_page_name(page.name),
            'path' => frame_path,
            'base64' => encode_file(frame_path)
          }
        end
      end

      def self.export_frames(model, directory, width: DEFAULT_WIDTH, height: DEFAULT_HEIGHT)
        FileUtils.mkdir_p(directory)
        capture_pages(model, width: width, height: height).map do |frame|
          target = File.join(directory, File.basename(frame['path']))
          FileUtils.cp(frame['path'], target)
          frame.merge('path' => target)
        end
      end

      def self.model_view(model)
        return model.active_view if model.respond_to?(:active_view)

        nil
      end

      def self.refresh_view(view)
        view.refresh if view&.respond_to?(:refresh)
      end

      def self.write_frame(view, path, width:, height:)
        if view&.respond_to?(:write_image)
          view.write_image(path, width, height, false, 0.0)
          return path if File.exist?(path)
        end

        write_placeholder_png(path, width: width, height: height)
        path
      end

      def self.write_placeholder_png(path, width:, height:)
        # Minimal valid 1x1 PNG for headless tests; scaled via HTML display size when capture unavailable.
        png = [
          0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
          0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
          0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
          0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,
          0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41,
          0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,
          0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,
          0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,
          0x42, 0x60, 0x82
        ].pack('C*')
        File.binwrite(path, png)
        Logger.warn("LOD capture placeholder written: #{path} (#{width}x#{height} requested)")
        path
      end

      def self.encode_file(path)
        return nil unless path && File.exist?(path)

        Base64.strict_encode64(File.binread(path))
      end

      def self.capture_cache_dir
        dir = File.join(Project.plugin_root, 'cache', 'lod_capture')
        FileUtils.mkdir_p(dir)
        dir
      end
    end
  end
end
