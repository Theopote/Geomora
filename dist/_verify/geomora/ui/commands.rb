# frozen_string_literal: true

module Geomora
  module UI
    module Commands
      class << self
        def register
          menu = ::UI.menu('Extensions').add_submenu('Geomora')

          menu.add_item('Generate Phase 0 Fixture') do
            run_generate
          end

          menu.add_item('Validate Phase 0 Fixture') do
            run_validate
          end
        end

        def run_generate
          path = Core::Project.fixture_path
          Core::Project.generate_from_file(path)
          ::UI.messagebox("Geomora generation complete.\n\nFixture: #{path}")
        rescue GeomoraError => e
          ::UI.messagebox("Geomora error:\n\n#{e.message}")
        end

        def run_validate
          path = Core::Project.fixture_path
          Core::Project.validate_file(path)
          ::UI.messagebox("Validation passed.\n\nFixture: #{path}")
        rescue GeomoraError => e
          ::UI.messagebox("Validation failed:\n\n#{e.message}")
        end
      end
    end
  end
end
