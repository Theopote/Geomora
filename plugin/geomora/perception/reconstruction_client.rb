# frozen_string_literal: true

require 'json'
require 'net/http'
require 'uri'

module Geomora
  module Perception
    class ReconstructionClient
      DEFAULT_HOST = '127.0.0.1'
      DEFAULT_PORT = 8765
      DEFAULT_TIMEOUT = 120

      class << self
        def reconstruct(image_path, method: 'auto', photo_id: 'workspace_photo', metric: nil, ai_settings: {}, cloud_upload_authorized: false,
                        host: DEFAULT_HOST, port: DEFAULT_PORT)
          raise GeomoraError, "Image not found: #{image_path}" unless File.exist?(image_path)

          boundary = "----GeomoraReconstruct#{rand(1_000_000)}"
          body = multipart_body(boundary, image_path, method, photo_id, metric, ai_settings, cloud_upload_authorized)
          request = Net::HTTP::Post.new(URI("http://#{host}:#{port}/reconstruct"))
          request['Content-Type'] = "multipart/form-data; boundary=#{boundary}"
          request.body = body
          response = Net::HTTP.start(host, port, read_timeout: DEFAULT_TIMEOUT, open_timeout: 5) do |http|
            http.request(request)
          end
          raise GeometryGenerationError, error_message(response) unless response.is_a?(Net::HTTPSuccess)

          JSON.parse(response.body)
        rescue Errno::ECONNREFUSED, SocketError
          raise GeometryGenerationError,
                'Reconstruction service is not running. Start backend on port 8765.'
        end

        private

        def multipart_body(boundary, image_path, method, photo_id, metric, ai_settings, cloud_upload_authorized)
          parts = []
          add_file(parts, boundary, image_path)
          add_field(parts, boundary, 'method', method)
          add_field(parts, boundary, 'photo_id', photo_id)
          add_field(parts, boundary, 'routing_mode', ai_settings['routing_mode'] || 'local_only')
          add_field(parts, boundary, 'vlm_provider', ai_settings['vlm_provider'] || 'openai')
          add_field(parts, boundary, 'vlm_model', ai_settings['vlm_model'] || 'auto')
          add_field(parts, boundary, 'vlm_base_url', ai_settings['vlm_base_url'] || '')
          add_field(parts, boundary, 'cloud_upload_authorized', cloud_upload_authorized)
          add_field(parts, boundary, 'depth_method', ai_settings['depth_method'] || 'auto')
          add_field(parts, boundary, 'onnx_device', ai_settings['onnx_device'] || 'auto')
          add_field(parts, boundary, 'wall_length_mm', metric[:width]) if metric && metric[:width].positive?
          add_field(parts, boundary, 'wall_height_mm', metric[:height]) if metric && metric[:height].positive?
          parts << "--#{boundary}--\r\n"
          parts.join
        end

        def add_file(parts, boundary, path)
          parts << "--#{boundary}\r\n"
          parts << "Content-Disposition: form-data; name=\"image\"; filename=\"#{File.basename(path)}\"\r\n"
          parts << "Content-Type: #{image_content_type(path)}\r\n\r\n"
          parts << File.binread(path)
          parts << "\r\n"
        end

        def add_field(parts, boundary, name, value)
          parts << "--#{boundary}\r\n"
          parts << "Content-Disposition: form-data; name=\"#{name}\"\r\n\r\n#{value}\r\n"
        end

        def image_content_type(path)
          File.extname(path).downcase == '.png' ? 'image/png' : 'image/jpeg'
        end

        def error_message(response)
          JSON.parse(response.body)['detail'] || response.message
        rescue JSON::ParserError
          response.message
        end
      end
    end
  end
end
