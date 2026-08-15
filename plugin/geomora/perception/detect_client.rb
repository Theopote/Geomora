# frozen_string_literal: true

require 'json'
require 'net/http'
require 'uri'
require 'base64'
require 'fileutils'

module Geomora
  module Perception
    class DetectClient
      DEFAULT_HOST = '127.0.0.1'
      DEFAULT_PORT = 8765
      DEFAULT_TIMEOUT = 60

      class << self
        def detect(image_path, host: DEFAULT_HOST, port: DEFAULT_PORT)
          raise GeomoraError, "Image not found: #{image_path}" unless File.exist?(image_path)

          response = post_multipart(host: host, port: port, image_path: image_path)

          unless response.is_a?(Net::HTTPSuccess)
            raise GeometryGenerationError, parse_error_message(response)
          end

          data = JSON.parse(response.body)
          save_overlay_image(data)
          DetectionResult.from_hash(data)
        rescue Errno::ECONNREFUSED, SocketError
          raise GeometryGenerationError,
                'Detection service is not running. Start backend: uvicorn geomora_rectify.server:app --port 8765'
        end

        private

        def post_multipart(host:, port:, image_path:)
          boundary = "----Geomora#{rand(1_000_000)}"
          body = build_body(boundary, image_path)

          uri = URI("http://#{host}:#{port}/detect")
          request = Net::HTTP::Post.new(uri)
          request['Content-Type'] = "multipart/form-data; boundary=#{boundary}"
          request.body = body

          Net::HTTP.start(host, port, read_timeout: DEFAULT_TIMEOUT, open_timeout: 5) do |http|
            http.request(request)
          end
        end

        def build_body(boundary, image_path)
          content_type = image_content_type(image_path)
          parts = []
          parts << "--#{boundary}\r\n"
          parts << "Content-Disposition: form-data; name=\"image\"; filename=\"#{File.basename(image_path)}\"\r\n"
          parts << "Content-Type: #{content_type}\r\n\r\n"
          parts << File.binread(image_path)
          parts << "\r\n"
          parts << "--#{boundary}--\r\n"
          parts.join
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

        def save_overlay_image(data)
          encoded = data['overlay_base64']
          return if encoded.nil? || encoded.empty?

          cache_dir = File.join(Core::Project.plugin_root, 'cache')
          FileUtils.mkdir_p(cache_dir)
          path = File.join(cache_dir, "detect_overlay_#{Time.now.to_i}.jpg")
          File.binwrite(path, Base64.decode64(encoded))
          data['overlay_image_path'] = path
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
