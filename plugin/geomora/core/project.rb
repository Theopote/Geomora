# frozen_string_literal: true

require 'json'

module Geomora
  module Core
    class Project
      def self.fixture_path
        File.join(plugin_root, 'examples', 'facade_phase0.json')
      end

      # Plugin root: plugin/geomora/ (dev) or Plugins/geomora/ (RBZ install)
      def self.plugin_root
        File.expand_path('..', __dir__)
      end

      def self.validate_file(path)
        validate_data(Loader.load_file(path))
        Logger.info("Validation passed: #{path}")
        true
      end

      def self.generate_from_file(path)
        data = Loader.load_file(path)
        generate_from_data(data)
      end

      def self.generate_from_data(data)
        document = parse_data(data)
        IR::Validator.validate(document)

        model = Sketchup.active_model
        Transactions::Operation.run('Geomora Generate', model) do
          Generators::ProjectGenerator.new(model).generate(document)
        end
      end

      def self.validate_data(data)
        document = parse_data(data)
        IR::Validator.validate(document)
        Logger.info('Validation passed')
        true
      end

      def self.rationalize_facade(params, grid_mm: Rationalizer::DEFAULT_GRID_MM)
        Rationalizer.rationalize(params, grid_mm: grid_mm)
      end

      def self.build_manual_facade(params)
        IRBuilder.build_manual_facade(params)
      end

      def self.load_and_parse(path)
        parse_data(Loader.load_file(path))
      end

      def self.parse_data(data)
        hash = data.is_a?(String) ? JSON.parse(data) : data
        IR::Parser.parse(hash)
      end
    end
  end
end
