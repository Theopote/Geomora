# frozen_string_literal: true

require 'json'
require 'net/http'

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
      end
    end
  end
end
