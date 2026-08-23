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
          add_a1_menu_items(menu)
          menu.add_separator
          menu.add_item('Generate Phase 0 Fixture') { run_generate }
          menu.add_item('Validate Phase 0 Fixture') { run_validate }
          menu.add_item('Repair Geometry') { run_repair_geometry }
          menu.add_separator
          add_lod_menu_items(menu)
          menu.add_separator
          menu.add_item('About Geomora') { show_about }
        end

        def add_a1_menu_items(menu)
          a1_menu = menu.add_submenu('A1 Real Photo Benchmark')
          a1_menu.add_item('Review Next Photo') { A1BenchmarkRunner.review_next }
          a1_menu.add_item('Record A1 Score...') { A1BenchmarkRunner.record_score }
          a1_menu.add_item('Show Progress') { A1BenchmarkRunner.show_progress }
          a1_menu.add_item('Open Checklist (HTML)') { A1BenchmarkRunner.open_checklist }
          a1_menu.add_item('Open Scores CSV') { A1BenchmarkRunner.open_scores_csv }
          a1_menu.add_separator
          a1_menu.add_item('Import A1 Scores to JSON') { A1BenchmarkRunner.import_scores }
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
          lod_menu.add_item('Save LOD Tour JSON...') { save_lod_tour_file }
          lod_menu.add_item('Export LOD Tour HTML...') { export_lod_tour_html }
          lod_menu.add_item('Export LOD Capture HTML...') { export_lod_tour_capture_html }
          lod_menu.add_item('Export LOD Tour Frames...') { export_lod_tour_frames }
          lod_menu.add_item('Export LOD Tour GIF...') { export_lod_tour_gif }
          lod_menu.add_item('Export LOD Tour MP4...') { export_lod_tour_mp4 }
          lod_menu.add_item('Export LOD Tour WebM...') { export_lod_tour_webm }
          lod_menu.add_item('Export LOD Tour MP4 (native)...') { export_lod_tour_mp4_native }
          lod_menu.add_item('Export LOD Tour MP4 (H.264)...') { export_lod_tour_h264_mp4 }
          lod_menu.add_item('Export LOD Tour AVI (native)...') { export_lod_tour_avi }
          lod_menu.add_item('Play LOD Tour') { play_lod_tour }
          lod_menu.add_separator
          lod_menu.add_item('Reload Fixture Catalog') { reload_fixture_catalog }
        end

        def save_lod_tour_file
          path = ::UI.savepanel('Save LOD tour manifest', '', 'geomora_lod_tour.json')
          return unless path

          saved = Core::Project.export_lod_tour(path)
          ::UI.messagebox("LOD tour saved:\n\n#{saved}")
        rescue GeomoraError => e
          ::UI.messagebox("LOD tour save failed:\n\n#{e.message}")
        end

        def export_lod_tour_html
          path = ::UI.savepanel('Export LOD tour HTML', '', 'geomora_lod_tour.html')
          return unless path

          saved = Core::Project.export_lod_tour_html(path)
          ::UI.messagebox("LOD tour HTML exported:\n\n#{saved}")
        rescue GeomoraError => e
          ::UI.messagebox("LOD tour HTML export failed:\n\n#{e.message}")
        end

        def export_lod_tour_capture_html
          path = ::UI.savepanel('Export LOD capture tour', '', 'geomora_lod_capture.html')
          return unless path

          saved = Core::Project.export_lod_tour_capture_html(path)
          ::UI.messagebox("LOD capture tour exported:\n\n#{saved}")
        rescue GeomoraError => e
          ::UI.messagebox("LOD capture export failed:\n\n#{e.message}")
        end

        def export_lod_tour_frames
          path = ::UI.select_directory('Export LOD tour frames')
          return unless path

          frames = Core::Project.export_lod_tour_frames(path)
          names = frames.map { |frame| File.basename(frame['path']) }.join("\n")
          ::UI.messagebox("LOD frames exported:\n\n#{names}")
        rescue GeomoraError => e
          ::UI.messagebox("LOD frame export failed:\n\n#{e.message}")
        end

        def export_lod_tour_gif
          path = ::UI.savepanel('Export LOD tour GIF', '', 'geomora_lod_tour.gif')
          return unless path

          saved = Core::Project.export_lod_tour_gif(path)
          ::UI.messagebox("LOD tour GIF exported:\n\n#{saved}")
        rescue GeomoraError => e
          ::UI.messagebox("LOD GIF export failed:\n\n#{e.message}")
        end

        def export_lod_tour_mp4
          path = ::UI.savepanel('Export LOD tour MP4', '', 'geomora_lod_tour.mp4')
          return unless path

          saved = Core::Project.export_lod_tour_video(path, format: 'mp4')
          message = saved.to_s.end_with?('.ps1', '.sh') ? "Frames exported. Run encoder script:\n\n#{saved}" : "LOD tour MP4 exported:\n\n#{saved}"
          ::UI.messagebox(message)
        rescue GeomoraError => e
          ::UI.messagebox("LOD MP4 export failed:\n\n#{e.message}")
        end

        def export_lod_tour_webm
          path = ::UI.savepanel('Export LOD tour WebM', '', 'geomora_lod_tour.webm')
          return unless path

          saved = Core::Project.export_lod_tour_video(path, format: 'webm')
          message = saved.to_s.end_with?('.ps1', '.sh') ? "Frames exported. Run encoder script:\n\n#{saved}" : "LOD tour WebM exported:\n\n#{saved}"
          ::UI.messagebox(message)
        rescue GeomoraError => e
          ::UI.messagebox("LOD WebM export failed:\n\n#{e.message}")
        end

        def export_lod_tour_avi
          path = ::UI.savepanel('Export LOD tour AVI (native)', '', 'geomora_lod_tour.avi')
          return unless path

          saved = Core::Project.export_lod_tour_avi(path)
          ::UI.messagebox("LOD tour AVI exported (no ffmpeg required):\n\n#{saved}")
        rescue GeomoraError => e
          ::UI.messagebox("LOD AVI export failed:\n\n#{e.message}")
        end

        def export_lod_tour_mp4_native
          path = ::UI.savepanel('Export LOD tour MP4 (native)', '', 'geomora_lod_tour.mp4')
          return unless path

          saved = Core::Project.export_lod_tour_mp4_native(path)
          ::UI.messagebox("LOD tour MP4 exported (no ffmpeg required):\n\n#{saved}")
        rescue GeomoraError => e
          ::UI.messagebox("LOD MP4 export failed:\n\n#{e.message}")
        end

        def export_lod_tour_h264_mp4
          path = ::UI.savepanel('Export LOD tour MP4 (H.264)', '', 'geomora_lod_tour_h264.mp4')
          return unless path

          saved = Core::Project.export_lod_tour_h264_mp4(path)
          ffmpeg = Core::LodVideoExporter.ffmpeg_path
          note = ffmpeg ? 'libx264 via ffmpeg' : 'native baseline H.264 (no ffmpeg)'
          ::UI.messagebox("LOD tour H.264 MP4 exported (#{note}):\n\n#{saved}")
        rescue GeomoraError => e
          ::UI.messagebox("LOD H.264 MP4 export failed:\n\n#{e.message}")
        end

        def reload_fixture_catalog
          catalog = Core::Project.reload_fixture_catalog
          sets = catalog['sets'].is_a?(Hash) ? catalog['sets'].keys.length : 0
          ::UI.messagebox("Fixture catalog reloaded (#{sets} room sets).")
        rescue GeomoraError => e
          ::UI.messagebox("Fixture catalog reload failed:\n\n#{e.message}")
        end

        def play_lod_tour
          pages = Core::Project.play_lod_tour
          ::UI.messagebox("LOD tour started:\n\n#{pages.join("\n")}")
        rescue GeomoraError => e
          ::UI.messagebox("LOD tour failed:\n\n#{e.message}")
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

        TOOLBAR_ICON_DIR = File.join(__dir__, 'toolbar').freeze

        def toolbar_icon(name, size)
          File.join(TOOLBAR_ICON_DIR, "#{name}_#{size}.png")
        end

        def configure_toolbar_command(command, icon:, tooltip:, status_bar_text:)
          command.tooltip = tooltip
          command.status_bar_text = status_bar_text
          command.small_icon = toolbar_icon(icon, 'small')
          command.large_icon = toolbar_icon(icon, 'large')
          command
        end

        def register_toolbar
          toolbar = ::UI::Toolbar.new('Geomora')

          workspace_cmd = configure_toolbar_command(
            ::UI::Command.new('工作面板') { open_workspace },
            icon: 'workspace',
            tooltip: '打开 Geomora 工作面板',
            status_bar_text: '打开重建工作区，进行照片导入、AI 分析与模型生成'
          )
          toolbar.add_item(workspace_cmd)

          generate_cmd = configure_toolbar_command(
            ::UI::Command.new('生成模型') { run_generate },
            icon: 'generate',
            tooltip: '生成默认立面模型',
            status_bar_text: '根据 Phase 0 样例 IR 在场景中生成默认建筑立面'
          )
          toolbar.add_item(generate_cmd)

          validate_cmd = configure_toolbar_command(
            ::UI::Command.new('验证样例') { run_validate },
            icon: 'validate',
            tooltip: '验证 IR 样例',
            status_bar_text: '校验 Phase 0 样例 IR，不生成几何体'
          )
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
