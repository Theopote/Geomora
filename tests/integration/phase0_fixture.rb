# frozen_string_literal: true

# SketchUp integration verification for Phase 0.
# Loaded automatically by the extension; can also be run from Ruby Console:
#   load 'F:/development/Geomora/tests/integration/phase0_fixture.rb'

module Geomora
  module Integration
    module Phase0Fixture
      def self.run
        path = Core::Project.fixture_path
        Logger.info("Integration test: validating #{path}")
        Core::Project.validate_file(path)

        Logger.info('Integration test: generating')
        Core::Project.generate_from_file(path)

        model = Sketchup.active_model
        project_groups = model.active_entities.grep(Sketchup::Group).select do |g|
          Metadata::Attributes.read(g, 'entity_type') == 'project'
        end

        window_defs = model.definitions.select do |d|
          d.name == 'window_standard_1500'
        end

        results = {
          project_count: project_groups.length,
          window_definition_count: window_defs.length,
          project_id: Metadata::Attributes.project_id(project_groups.first)
        }

        Logger.info("Integration results: #{results}")
        results
      end
    end
  end
end
