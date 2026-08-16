# frozen_string_literal: true

require 'fileutils'

module Geomora
  module Core
    class LodVideoExporter
      DEFAULT_FPS = 0.5
      FFMPEG_NAMES = %w[ffmpeg ffmpeg.exe].freeze

      def self.export(model, path, format: 'mp4', fps: DEFAULT_FPS, width: LodCapture::DEFAULT_WIDTH, height: LodCapture::DEFAULT_HEIGHT)
        frames = LodCapture.export_frames(model, frames_workspace(path), width: width, height: height)
        raise GeomoraError, 'No Geomora LOD scenes found. Create LOD Scene Pages first.' if frames.empty?

        ffmpeg = ffmpeg_path
        if ffmpeg
          encode_with_ffmpeg(ffmpeg, frames, path, format: format, fps: fps)
          path
        elsif format.to_s.downcase == 'mp4'
          avi_path = path.sub(/\.mp4\z/i, '.avi')
          rgb_frames = frames.map { |frame| LodCapture.frame_rgb(frame['path']) }
          begin
            Mp4Encoder.encode(rgb_frames, path, fps: fps)
            Logger.info("Native MP4 exported: #{path}")
            path
          rescue StandardError => e
            Logger.warn("Native MP4 failed (#{e.message}); falling back to AVI")
            AviEncoder.encode(rgb_frames, avi_path, fps: fps)
            avi_path
          end
        else
          script_path = write_encode_script(frames, path, format: format, fps: fps)
          Logger.warn("ffmpeg not found; wrote encoder script: #{script_path}")
          script_path
        end
      end

      def self.export_native_mp4(model, path, fps: DEFAULT_FPS, width: LodCapture::DEFAULT_WIDTH, height: LodCapture::DEFAULT_HEIGHT)
        frames = LodCapture.capture_pages(model, width: width, height: height).map do |frame|
          LodCapture.frame_rgb(frame['path'])
        end
        Mp4Encoder.encode(frames, path, fps: fps)
      end

      def self.export_h264_mp4(model, path, fps: DEFAULT_FPS, width: LodCapture::DEFAULT_WIDTH, height: LodCapture::DEFAULT_HEIGHT)
        frames = LodCapture.capture_pages(model, width: width, height: height).map do |frame|
          LodCapture.frame_rgb(frame['path'])
        end
        raise GeomoraError, 'No Geomora LOD scenes found. Create LOD Scene Pages first.' if frames.empty?

        ffmpeg = ffmpeg_path
        if ffmpeg
          workspace = frames_workspace(path)
          png_frames = LodCapture.export_frames(model, workspace, width: width, height: height)
          encode_with_ffmpeg(ffmpeg, png_frames, path, format: 'mp4', fps: fps)
          Logger.info("H.264 MP4 exported via ffmpeg: #{path}")
          return path
        end

        H264Mp4Encoder.encode(frames, path, fps: fps)
        Logger.info("Native H.264 MP4 exported: #{path}")
        path
      end

      def self.ffmpeg_path
        FFMPEG_NAMES.each do |name|
          path = executable_on_path(name)
          return path if path
        end
        nil
      end

      def self.executable_on_path(name)
        ENV.fetch('PATH', '').split(File::PATH_SEPARATOR).each do |dir|
          candidate = File.join(dir, name)
          return candidate if File.exist?(candidate)
        end
        nil
      end

      def self.frames_workspace(output_path)
        base = File.basename(output_path, '.*')
        dir = File.join(LodCapture.capture_cache_dir, "#{base}_frames")
        FileUtils.mkdir_p(dir)
        dir
      end

      def self.encode_with_ffmpeg(ffmpeg, frames, path, format:, fps:)
        input_pattern = File.join(File.dirname(frames.first['path']), 'lod_frame_%03d.png')
        args = [
          ffmpeg, '-y',
          '-framerate', fps.to_s,
          '-i', input_pattern,
          '-pix_fmt', 'yuv420p'
        ]
        args += codec_args(format)
        args << path
        run_command(args)
        path
      end

      def self.codec_args(format)
        case format.to_s.downcase
        when 'webm'
          ['-c:v', 'libvpx-vp9', '-b:v', '1M']
        else
          ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23']
        end
      end

      def self.run_command(args)
        require 'open3'
        stdout, stderr, status = Open3.capture3(*args)
        return if status.success?

        raise GeomoraError, "ffmpeg failed: #{stderr.strip.empty? ? stdout.strip : stderr.strip}"
      rescue LoadError
        system(*args) || raise(GeomoraError, "ffmpeg failed: #{args.join(' ')}")
      end

      def self.write_encode_script(frames, path, format:, fps:)
        dir = File.dirname(frames.first['path'])
        pattern = File.join(dir, 'lod_frame_%03d.png')
        ext = format.to_s.downcase == 'webm' ? 'webm' : 'mp4'
        output = path.end_with?(".#{ext}") ? path : "#{path}.#{ext}"
        if Gem.win_platform?
          script = File.join(dir, 'encode_lod_tour.ps1')
          codec = format.to_s.downcase == 'webm' ? 'libvpx-vp9' : 'libx264'
          File.write(
            script,
            <<~PS1
              $ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
              if (-not $ffmpeg) { throw 'ffmpeg not found in PATH' }
              & ffmpeg -y -framerate #{fps} -i "#{pattern.gsub('/', '\\')}" -c:v #{codec} -pix_fmt yuv420p "#{output.gsub('/', '\\')}"
            PS1
          )
          script
        else
          script = File.join(dir, 'encode_lod_tour.sh')
          codec_flag = format.to_s.downcase == 'webm' ? 'libvpx-vp9' : 'libx264'
          File.write(
            script,
            <<~SH
              #!/usr/bin/env bash
              set -euo pipefail
              ffmpeg -y -framerate #{fps} -i "#{pattern}" -c:v #{codec_flag} -pix_fmt yuv420p "#{output}"
            SH
          )
          File.chmod(0o755, script)
          script
        end
      end
    end
  end
end
