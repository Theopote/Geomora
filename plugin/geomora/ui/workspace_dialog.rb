# frozen_string_literal: true

require 'json'

module Geomora
  module AppUI
    class WorkspaceDialog
      WORKSPACE_DIR = File.join(Core::Project.plugin_root, 'ui', 'workspace')
      HTML_PATH = File.join(WORKSPACE_DIR, 'index.html')

      class << self
        def show
          @dialog ||= build_dialog
          @dialog.show
        end

        def bring_to_front
          show
          @dialog.bring_to_front if @dialog&.visible?
        end

        private

        def build_dialog
          dialog = ::UI::HtmlDialog.new(
            dialog_title: 'Geomora Workspace',
            preferences_key: 'geomora_workspace_v1',
            scrollable: false,
            resizable: true,
            width: 1200,
            height: 760,
            style: ::UI::HtmlDialog::STYLE_DIALOG
          )

          register_callbacks(dialog)
          dialog.set_file(HTML_PATH)
          dialog
        end

        def register_callbacks(dialog)
          dialog.add_action_callback('ready') do |_ctx, _|
            payload = default_payload
            dialog.execute_script("window.geomora.loadPayload(#{payload.to_json})")
          end

          dialog.add_action_callback('pick_image') do |_ctx, _|
            path = ::UI.openpanel('Select facade reference image', '', 'Images|*.jpg;*.jpeg;*.png;*.webp;||')
            if path
              file_url = path_to_file_url(path)
              dialog.execute_script("window.geomora.setImage(#{file_url.to_json}, #{path.to_json})")
            end
          end

          dialog.add_action_callback('load_template') do |_ctx, _|
            data = JSON.parse(File.read(Core::Project.fixture_path))
            dialog.execute_script("window.geomora.loadPayload(#{payload_from_ir(data).to_json})")
          end

          dialog.add_action_callback('validate') do |_ctx, json|
            params = JSON.parse(json)
            ir = Core::Project.build_manual_facade(params)
            Core::Project.validate_data(ir)
            post_message(dialog, 'success', 'Validation passed.')
            dialog.execute_script("window.geomora.setIrPreview(#{ir.to_json})")
          rescue GeomoraError => e
            post_message(dialog, 'error', e.message)
          end

          dialog.add_action_callback('generate') do |_ctx, json|
            params = JSON.parse(json)
            ir = Core::Project.build_manual_facade(params)
            Core::Project.generate_from_data(ir)
            post_message(dialog, 'success', 'Generation complete.')
            dialog.execute_script("window.geomora.setIrPreview(#{ir.to_json})")
          rescue GeomoraError => e
            post_message(dialog, 'error', e.message)
          end
        end

        def default_payload
          data = JSON.parse(File.read(Core::Project.fixture_path))
          payload_from_ir(data)
        end

        def payload_from_ir(data)
          wall = data.dig('buildings', 0, 'storeys', 0, 'elements', 0, 'geometry') || {}
          openings = data['openings'] || []
          windows = openings.select { |o| o['type'] == 'window' }.map do |win|
            {
              'offset' => win.dig('geometry', 'offset'),
              'width' => win.dig('geometry', 'width'),
              'height' => win.dig('geometry', 'height'),
              'sill_height' => win.dig('geometry', 'sill_height')
            }
          end
          door = openings.find { |o| o['type'] == 'door' }
          door_payload = if door
                             {
                               'offset' => door.dig('geometry', 'offset'),
                               'width' => door.dig('geometry', 'width'),
                               'height' => door.dig('geometry', 'height')
                             }
                           else
                             {}
                           end

          {
            'project_name' => data.dig('project', 'name') || 'Manual Facade',
            'wall_length' => distance(wall['baseline']),
            'wall_height' => wall['height'],
            'wall_thickness' => wall['thickness'],
            'windows' => windows,
            'door' => door_payload,
            'source_path' => nil,
            'source_id' => nil,
            'ir_preview' => data
          }
        end

        def distance(baseline)
          return 0 unless baseline.is_a?(Array) && baseline.length == 2

          a = baseline[0]
          b = baseline[1]
          Math.sqrt((b[0] - a[0])**2 + (b[1] - a[1])**2 + (b[2] - a[2])**2)
        end

        def path_to_file_url(path)
          normalized = path.gsub('\\', '/')
          "file:///#{normalized}"
        end

        def post_message(dialog, level, message)
          dialog.execute_script("window.geomora.setStatus(#{level.to_json}, #{message.to_json})")
        end
      end
    end
  end
end
