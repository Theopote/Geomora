# frozen_string_literal: true

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
        document = load_and_parse(path)
        IR::Validator.validate(document)
        Logger.info("Validation passed: #{path}")
        true
      end

      def self.generate_from_file(path)
        document = load_and_parse(path)
        IR::Validator.validate(document)

        model = Sketchup.active_model
        Transactions::Operation.run('Geomora Generate', model) do
          Generators::ProjectGenerator.new(model).generate(document)
        end
      end

      def self.load_and_parse(path)
        data = Loader.load_file(path)
        IR::Parser.parse(data)
      end
    end
  end
end
