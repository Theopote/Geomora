# frozen_string_literal: true

require 'fileutils'
require 'base64'
require 'zlib'

require_relative 'project'

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
        width = [width.to_i, 1].max
        height = [height.to_i, 1].max
        png = build_placeholder_png(width, height)
        File.binwrite(path, png)
        Logger.warn("LOD capture placeholder written: #{path} (#{width}x#{height})")
        path
      end

      def self.build_placeholder_png(width, height)
        raw = +''
        height.times do |y|
          raw << 0
          width.times do |x|
            raw << ((x * 255) / width).chr
            raw << ((y * 255) / height).chr
            raw << 120.chr
          end
        end

        signature = [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A].pack('C*')
        ihdr = [width, height, 8, 2, 0, 0, 0].pack('NNCCCCC')
        idat = Zlib::Deflate.deflate(raw)

        signature + png_chunk('IHDR', ihdr) + png_chunk('IDAT', idat) + png_chunk('IEND', +'')
      end

      def self.png_chunk(type, data)
        crc_input = type + data
        [data.bytesize].pack('N') + crc_input + [Zlib.crc32(crc_input)].pack('N')
      end

      def self.encode_file(path)
        return nil unless path && File.exist?(path)

        Base64.strict_encode64(File.binread(path))
      end

      def self.capture_cache_dir
        dir = File.join(Geomora::Core::Project.plugin_root, 'cache', 'lod_capture')
        FileUtils.mkdir_p(dir)
        dir
      end

      def self.frame_rgb(path)
        PngReader.read_rgb(path)
      rescue GeomoraError, StandardError => e
        Logger.warn("LOD frame RGB decode failed: #{e.message}")
        placeholder_rgb(DEFAULT_WIDTH, DEFAULT_HEIGHT)
      end

      def self.placeholder_rgb(width, height)
        rgb = +''
        height.times do |y|
          width.times do |x|
            rgb << ((x * 255) / [width, 1].max).chr
            rgb << ((y * 255) / [height, 1].max).chr
            rgb << 120.chr
          end
        end
        { 'width' => width, 'height' => height, 'rgb' => rgb }
      end

      def self.export_gif(model, path, delay_centiseconds: 20, width: DEFAULT_WIDTH, height: DEFAULT_HEIGHT)
        frames = capture_pages(model, width: width, height: height).map do |frame|
          frame_rgb(frame['path'])
        end
        GifEncoder.encode(frames, path, delay_centiseconds: delay_centiseconds)
      end

      def self.export_avi(model, path, fps: LodVideoExporter::DEFAULT_FPS, width: DEFAULT_WIDTH, height: DEFAULT_HEIGHT)
        frames = capture_pages(model, width: width, height: height).map do |frame|
          frame_rgb(frame['path'])
        end
        AviEncoder.encode(frames, path, fps: fps)
      end
    end
  end
end
