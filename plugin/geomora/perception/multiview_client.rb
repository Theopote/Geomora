# frozen_string_literal: true

require 'json'
require 'net/http'
require 'uri'

module Geomora
  module Perception
    class MultiviewClient
      DEFAULT_HOST = '127.0.0.1'
      DEFAULT_PORT = 8765
      DEFAULT_TIMEOUT = 60

      class << self
        def register(primary_path, secondary_path, host: DEFAULT_HOST, port: DEFAULT_PORT)
          raise GeomoraError, "Primary image not found: #{primary_path}" unless File.exist?(primary_path)
          raise GeomoraError, "Secondary image not found: #{secondary_path}" unless File.exist?(secondary_path)

          response = post_multipart(
            host: host,
            port: port,
            primary_path: primary_path,
            secondary_path: secondary_path
          )

          unless response.is_a?(Net::HTTPSuccess)
            raise GeometryGenerationError, parse_error_message(response)
          end

          MultiviewResult.from_hash(JSON.parse(response.body))
        rescue Errno::ECONNREFUSED, SocketError
          raise GeometryGenerationError,
                'Perception service is not running. Start backend: backend/start_server.bat'
        end

        def fuse(primary_path, secondary_path, homography: nil, method: 'auto', host: DEFAULT_HOST, port: DEFAULT_PORT)
          raise GeomoraError, "Primary image not found: #{primary_path}" unless File.exist?(primary_path)
          raise GeomoraError, "Secondary image not found: #{secondary_path}" unless File.exist?(secondary_path)

          response = post_fuse_multipart(
            host: host,
            port: port,
            primary_path: primary_path,
            secondary_path: secondary_path,
            homography: homography,
            method: method
          )

          unless response.is_a?(Net::HTTPSuccess)
            raise GeometryGenerationError, parse_error_message(response)
          end

          FusionResult.from_hash(JSON.parse(response.body))
        rescue Errno::ECONNREFUSED, SocketError
          raise GeometryGenerationError,
                'Perception service is not running. Start backend: backend/start_server.bat'
        end

        private

        def post_multipart(host:, port:, primary_path:, secondary_path:)
          boundary = "----Geomora#{rand(1_000_000)}"
          body = build_register_body(boundary, primary_path, secondary_path)

          uri = URI("http://#{host}:#{port}/multiview/register")
          request = Net::HTTP::Post.new(uri)
          request['Content-Type'] = "multipart/form-data; boundary=#{boundary}"
          request.body = body

          Net::HTTP.start(host, port, read_timeout: DEFAULT_TIMEOUT, open_timeout: 5) do |http|
            http.request(request)
          end
        end

        def build_register_body(boundary, primary_path, secondary_path)
          parts = []
          parts << file_part(boundary, 'primary', primary_path)
          parts << file_part(boundary, 'secondary', secondary_path)
          parts << "--#{boundary}--\r\n"
          parts.join
        end

        def post_fuse_multipart(host:, port:, primary_path:, secondary_path:, homography:, method:)
          boundary = "----Geomora#{rand(1_000_000)}"
          body = build_fuse_body(boundary, primary_path, secondary_path, homography, method)

          uri = URI("http://#{host}:#{port}/multiview/fuse")
          request = Net::HTTP::Post.new(uri)
          request['Content-Type'] = "multipart/form-data; boundary=#{boundary}"
          request.body = body

          Net::HTTP.start(host, port, read_timeout: DEFAULT_TIMEOUT, open_timeout: 5) do |http|
            http.request(request)
          end
        end

        def build_fuse_body(boundary, primary_path, secondary_path, homography, method)
          parts = []
          parts << file_part(boundary, 'primary', primary_path)
          parts << file_part(boundary, 'secondary', secondary_path)
          if homography
            parts << "--#{boundary}\r\n"
            parts << "Content-Disposition: form-data; name=\"homography\"\r\n\r\n"
            parts << homography.is_a?(String) ? homography : homography.to_json
            parts << "\r\n"
          end
          parts << "--#{boundary}\r\n"
          parts << "Content-Disposition: form-data; name=\"method\"\r\n\r\n"
          parts << method.to_s
          parts << "\r\n"
          parts << "--#{boundary}--\r\n"
          parts.join
        end

        def file_part(boundary, field_name, path)
          content_type = image_content_type(path)
          part = []
          part << "--#{boundary}\r\n"
          part << "Content-Disposition: form-data; name=\"#{field_name}\"; filename=\"#{File.basename(path)}\"\r\n"
          part << "Content-Type: #{content_type}\r\n\r\n"
          part << File.binread(path)
          part << "\r\n"
          part.join
        end

        def image_content_type(path)
          case File.extname(path).downcase
          when '.jpg', '.jpeg' then 'image/jpeg'
          when '.png' then 'image/png'
          when '.webp' then 'image/webp'
          when '.bmp' then 'image/bmp'
          when '.gif' then 'image/gif'
          else 'image/jpeg'
          end
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
