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
        else
          script_path = write_encode_script(frames, path, format: format, fps: fps)
          Logger.warn("ffmpeg not found; wrote encoder script: #{script_path}")
          script_path
        end
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
