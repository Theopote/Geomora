# frozen_string_literal: true

require 'json'
require 'net/http'
require 'uri'
require 'base64'
require 'fileutils'

module Geomora
  module Perception
    class RectifyClient
      DEFAULT_HOST = '127.0.0.1'
      DEFAULT_PORT = 8765
      DEFAULT_TIMEOUT = 60

      class << self
        def rectify(image_path, corners: nil, host: DEFAULT_HOST, port: DEFAULT_PORT)
          raise GeomoraError, "Image not found: #{image_path}" unless File.exist?(image_path)

          response = post_multipart(
            host: host,
            port: port,
            image_path: image_path,
            corners: corners
          )

          unless response.is_a?(Net::HTTPSuccess)
            raise GeometryGenerationError, parse_error_message(response)
          end

          data = JSON.parse(response.body)
          save_rectified_image(data)
          RectificationResult.from_hash(data)
        rescue Errno::ECONNREFUSED, SocketError
          raise GeometryGenerationError,
                'Rectify service is not running. Start backend: uvicorn geomora_rectify.server:app --port 8765'
        end

        def health(host: DEFAULT_HOST, port: DEFAULT_PORT)
          uri = URI("http://#{host}:#{port}/health")
          response = Net::HTTP.get_response(uri)
          response.is_a?(Net::HTTPSuccess)
        rescue StandardError
          false
        end

        private

        def post_multipart(host:, port:, image_path:, corners:)
          boundary = "----Geomora#{rand(1_000_000)}"
          body = build_body(boundary, image_path, corners)

          uri = URI("http://#{host}:#{port}/rectify")
          request = Net::HTTP::Post.new(uri)
          request['Content-Type'] = "multipart/form-data; boundary=#{boundary}"
          request.body = body

          Net::HTTP.start(host, port, read_timeout: DEFAULT_TIMEOUT, open_timeout: 5) do |http|
            http.request(request)
          end
        end

        def build_body(boundary, image_path, corners)
          parts = []
          parts << "--#{boundary}\r\n"
          parts << "Content-Disposition: form-data; name=\"image\"; filename=\"#{File.basename(image_path)}\"\r\n"
          parts << "Content-Type: application/octet-stream\r\n\r\n"
          parts << File.binread(image_path)
          parts << "\r\n"

          if corners
            parts << "--#{boundary}\r\n"
            parts << "Content-Disposition: form-data; name=\"corners\"\r\n\r\n"
            parts << corners.to_json
            parts << "\r\n"
          end

          parts << "--#{boundary}--\r\n"
          parts.join
        end

        def save_rectified_image(data)
          encoded = data['rectified_image_base64']
          return if encoded.nil? || encoded.empty?

          cache_dir = File.join(Core::Project.plugin_root, 'cache')
          FileUtils.mkdir_p(cache_dir)
          path = File.join(cache_dir, "rectified_#{Time.now.to_i}.jpg")
          File.binwrite(path, Base64.decode64(encoded))
          data['rectified_image_path'] = path
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
