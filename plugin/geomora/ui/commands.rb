# frozen_string_literal: true

require 'json'

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
          menu.add_item('Repair Geometry') { run_repair_geometry }
          menu.add_separator
          add_lod_menu_items(menu)
          menu.add_separator
          menu.add_item('About Geomora') { show_about }
        end

        def add_lod_menu_items(menu)
          lod_menu = menu.add_submenu('LOD View')
          lod_menu.add_item('LOD 100 — Massing') { apply_lod(:lod_100) }
          lod_menu.add_item('LOD 200 — Openings') { apply_lod(:lod_200) }
          lod_menu.add_item('LOD 300 — Details') { apply_lod(:lod_300) }
          lod_menu.add_separator
          lod_menu.add_item('Create LOD Scene Pages') { create_lod_scenes }
          lod_menu.add_item('Next LOD Scene') { next_lod_scene }
          lod_menu.add_item('Export LOD Tour Manifest') { export_lod_tour }
        end

        def export_lod_tour
          manifest = Core::Project.lod_tour_manifest
          ::UI.messagebox("LOD tour manifest:\n\n#{JSON.pretty_generate(manifest)}")
        rescue GeomoraError => e
          ::UI.messagebox("LOD tour export failed:\n\n#{e.message}")
        end

        def next_lod_scene
          name = Core::Project.next_lod_scene
          ::UI.messagebox("LOD scene: #{name}")
        rescue GeomoraError => e
          ::UI.messagebox("LOD scene failed:\n\n#{e.message}")
        end

        def create_lod_scenes
          pages = Core::Project.create_lod_scene_pages
          ::UI.messagebox("LOD scene pages created:\n\n#{pages.join("\n")}")
        rescue GeomoraError => e
          ::UI.messagebox("LOD scene pages failed:\n\n#{e.message}")
        end

        def apply_lod(preset)
          label = Core::Project.apply_lod_preset(preset)
          ::UI.messagebox("LOD view applied: #{label}")
        rescue GeomoraError => e
          ::UI.messagebox("LOD view failed:\n\n#{e.message}")
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

        def run_repair_geometry
          report = Core::Project.repair_geometry
          summary = report.select { |k, v| v.is_a?(Numeric) && v.positive? }
                          .map { |k, v| "#{k}: #{v}" }
                          .join("\n")
          message = summary.empty? ? 'No geometry issues repaired.' : summary
          ::UI.messagebox("Geometry doctor complete.\n\n#{message}")
        rescue GeomoraError => e
          ::UI.messagebox("Geometry doctor failed:\n\n#{e.message}")
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
