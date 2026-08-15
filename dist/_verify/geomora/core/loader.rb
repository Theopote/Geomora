# frozen_string_literal: true

require 'json'

module Geomora
  module Core
    class Loader
      def self.load_file(path)
        Logger.info("Loading IR from #{path}")
        unless File.exist?(path)
          raise GeomoraError, "IR file not found: #{path}"
        end

        raw = File.read(path)
        data = JSON.parse(raw)
        Logger.info('IR loaded')
        data
      rescue JSON::ParserError => e
        raise GeomoraError, "Invalid JSON in #{path}: #{e.message}"
      end
    end
  end
end
