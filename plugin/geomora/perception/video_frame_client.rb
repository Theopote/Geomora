# frozen_string_literal: true

require 'base64'
require 'json'
require 'net/http'
require 'uri'
require 'fileutils'

module Geomora
  module Perception
    class VideoFrameClient
      DEFAULT_HOST = '127.0.0.1'
      DEFAULT_PORT = 8765
      DEFAULT_TIMEOUT = 120

      class << self
        def extract_frames(video_path, max_frames: 12, host: DEFAULT_HOST, port: DEFAULT_PORT)
          raise GeomoraError, "Video not found: #{video_path}" unless File.exist?(video_path)

          response = post_multipart(
            host: host,
            port: port,
            video_path: video_path,
            max_frames: max_frames
          )

          unless response.is_a?(Net::HTTPSuccess)
            raise GeometryGenerationError, parse_error_message(response)
          end

          data = JSON.parse(response.body)
          persist_frames(data)
          data
        rescue Errno::ECONNREFUSED, SocketError
          raise GeometryGenerationError,
                'Video service is not running. Start backend: backend/start_server.bat'
        end

        private

        def post_multipart(host:, port:, video_path:, max_frames:)
          boundary = "----GeomoraVideo#{rand(1_000_000)}"
          body = build_body(boundary, video_path, max_frames)

          uri = URI("http://#{host}:#{port}/video/extract_frames")
          request = Net::HTTP::Post.new(uri)
          request['Content-Type'] = "multipart/form-data; boundary=#{boundary}"
          request.body = body

          Net::HTTP.start(host, port, read_timeout: DEFAULT_TIMEOUT, open_timeout: 5) do |http|
            http.request(request)
          end
        end

        def build_body(boundary, video_path, max_frames)
          parts = []
          parts << "--#{boundary}\r\n"
          parts << "Content-Disposition: form-data; name=\"video\"; filename=\"#{File.basename(video_path)}\"\r\n"
          parts << "Content-Type: #{video_content_type(video_path)}\r\n\r\n"
          parts << File.binread(video_path)
          parts << "\r\n"
          parts << "--#{boundary}\r\n"
          parts << "Content-Disposition: form-data; name=\"max_frames\"\r\n\r\n"
          parts << max_frames.to_s
          parts << "\r\n"
          parts << "--#{boundary}--\r\n"
          parts.join
        end

        def video_content_type(path)
          case File.extname(path).downcase
          when '.mov' then 'video/quicktime'
          when '.webm' then 'video/webm'
          when '.avi' then 'video/x-msvideo'
          when '.mkv' then 'video/x-matroska'
          else 'video/mp4'
          end
        end

        def persist_frames(data)
          cache_dir = File.join(Core::Project.plugin_root, 'cache', "video_#{Time.now.to_i}")
          FileUtils.mkdir_p(cache_dir)
          data['frames'].each_with_index do |frame, index|
            image_bytes = frame['image_base64']
            next if image_bytes.nil? || image_bytes.empty?

            image_path = File.join(cache_dir, "frame_#{index + 1}.jpg")
            File.binwrite(image_path, Base64.decode64(image_bytes))
            frame['path'] = image_path
            frame.delete('image_base64')

            if frame['thumb_base64']
              thumb_path = File.join(cache_dir, "thumb_#{index + 1}.jpg")
              File.binwrite(thumb_path, Base64.decode64(frame['thumb_base64']))
              frame['thumb_path'] = thumb_path
            end
          end
          data['cache_dir'] = cache_dir
        end

        def parse_error_message(response)
          body = JSON.parse(response.body)
          body['detail'] || response.message
        rescue JSON::ParserError
          response.message
        end
      end
    end
  end
end
