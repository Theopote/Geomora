# frozen_string_literal: true

require 'json'
require 'net/http'
require 'uri'

module Geomora
  module Perception
    class SettingsClient
      class << self
        def capabilities(host: '127.0.0.1', port: 8765)
          response = Net::HTTP.start(host, port, read_timeout: 5, open_timeout: 2) do |http|
            http.get('/settings/capabilities')
          end
          raise GeometryGenerationError, response.message unless response.is_a?(Net::HTTPSuccess)

          JSON.parse(response.body)
        rescue Errno::ECONNREFUSED, SocketError
          { 'service_available' => false, 'message' => 'Perception service is not running.' }
        end

        def configure_credentials(provider:, api_key:, base_url:, host: '127.0.0.1', port: 8765)
          request = Net::HTTP::Post.new('/settings/credentials')
          request['Content-Type'] = 'application/json'
          request.body = JSON.generate(provider: provider, api_key: api_key, base_url: base_url)
          response = Net::HTTP.start(host, port, read_timeout: 5, open_timeout: 2) { |http| http.request(request) }
          raise GeometryGenerationError, response.body unless response.is_a?(Net::HTTPSuccess)

          JSON.parse(response.body)
        rescue Errno::ECONNREFUSED, SocketError
          raise GeometryGenerationError, 'Perception service is not running.'
        end
      end
    end
  end
end
