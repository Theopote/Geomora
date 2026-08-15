# frozen_string_literal: true

module Geomora
  module AppUI
    module Commands
      class << self
        def register
          register_menu
          register_toolbar
          Geomora::Logger.info('UI registered (menu + toolbar)')
        end

        def register_menu
          %w[Extensions Plugins].each do |menu_name|
            begin
              parent = ::UI.menu(menu_name)
              submenu = parent.add_submenu('Geomora')
              add_menu_items(submenu)
            rescue StandardError => e
              Geomora::Logger.warn("Could not register #{menu_name} menu: #{e.message}")
            end
          end
        end

        def add_menu_items(menu)
          menu.add_item('Open Workspace') { open_workspace }
          menu.add_separator
          menu.add_item('Generate Phase 0 Fixture') { run_generate }
          menu.add_item('Validate Phase 0 Fixture') { run_validate }
          menu.add_separator
          menu.add_item('About Geomora') { show_about }
        end

        def register_toolbar
          toolbar = ::UI::Toolbar.new('Geomora')

          workspace_cmd = ::UI::Command.new('Workspace') { open_workspace }
          workspace_cmd.tooltip = 'Open Geomora Workspace'
          workspace_cmd.status_bar_text = 'Manual facade definition workspace'
          toolbar.add_item(workspace_cmd)

          generate_cmd = ::UI::Command.new('Generate') { run_generate }
          generate_cmd.tooltip = 'Generate Phase 0 Fixture'
          generate_cmd.status_bar_text = 'Build facade model from IR fixture'
          toolbar.add_item(generate_cmd)

          validate_cmd = ::UI::Command.new('Validate') { run_validate }
          validate_cmd.tooltip = 'Validate Phase 0 Fixture'
          validate_cmd.status_bar_text = 'Validate IR fixture without generating geometry'
          toolbar.add_item(validate_cmd)

          toolbar.restore
          toolbar.show
        end

        def open_workspace
          WorkspaceDialog.show
        rescue StandardError => e
          ::UI.messagebox("Failed to open workspace:\n\n#{e.message}")
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

        def show_about
          ::UI.messagebox(
            "Geomora v#{Geomora::VERSION}\n\n" \
            "Phase 2 — Reconstruction Workspace + Rectification\n\n" \
            "Extensions → Geomora → Open Workspace"
          )
        end
      end
    end
  end
end
