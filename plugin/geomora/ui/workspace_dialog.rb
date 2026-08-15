# frozen_string_literal: true

require 'json'

module Geomora
  module AppUI
    class WorkspaceDialog
      WORKSPACE_DIR = File.join(Core::Project.plugin_root, 'ui', 'workspace')
      HTML_PATH = File.join(WORKSPACE_DIR, 'index.html')
      REVIEW_WINDOW_LIMIT = Core::DetectionMapper::REVIEW_WINDOW_LIMIT

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
              @source_path = path
              file_url = path_to_file_url(path)
              dialog.execute_script("window.geomora.setImage(#{file_url.to_json}, #{path.to_json})")
            end
          end

          dialog.add_action_callback('rectify') do |_ctx, json|
            params = JSON.parse(json)
            source_path = params['source_path']
            if source_path.nil? || source_path.empty?
              raise GeomoraError, 'Load a reference image before rectifying.'
            end

            Logger.info("Rectifying image: #{source_path}")
            result = Perception::RectifyClient.rectify(source_path)
            @rectification = result.to_source_metadata(source_path)
            @rectified_image_path = result.rectified_image_path
            rectified_url = path_to_file_url(result.rectified_image_path)

            dialog.execute_script(
              "window.geomora.setRectifiedImage(#{rectified_url.to_json}, #{result.to_dict.to_json})"
            )
            post_message(
              dialog,
              'success',
              format('Rectified (confidence %.2f, %s)', result.confidence, result.method)
            )
          rescue GeomoraError => e
            post_message(dialog, 'error', e.message)
          end

          dialog.add_action_callback('detect') do |_ctx, json|
            params = JSON.parse(json)
            image_path = detection_image_path(params)
            if image_path.nil? || image_path.empty?
              raise GeomoraError, 'Load an image (and rectified view recommended) before detecting.'
            end

            Logger.info("Detecting facade elements: #{image_path}")
            result = Perception::DetectClient.detect(image_path)
            mapped = Core::DetectionMapper.to_facade_params(
              result,
              wall_length: params['wall_length'],
              wall_height: params['wall_height'],
              wall_thickness: params['wall_thickness']
            )
            @detection = result.to_source_metadata
            overlay_url = nil
            if result.overlay_base64 && !result.overlay_base64.empty?
              overlay_path = save_overlay_from_result(result)
              overlay_url = path_to_file_url(overlay_path) if overlay_path
            end

            if result.elements.empty?
              dialog.execute_script(
                "window.geomora.setDetectionMeta(#{result.to_dict.to_json}, #{overlay_url.to_json})"
              )
              post_message(
                dialog,
                'error',
                'No openings detected. Rectify first, then set wall size manually or edit openings by hand.'
              )
            else
              payload = mapped.merge('detection' => result.to_dict)
              dialog.execute_script(
                "window.geomora.applyDetection(#{payload.to_json}, #{overlay_url.to_json})"
              )
              window_count = result.to_dict['windows']
              door_count = result.to_dict['doors']
              if window_count > REVIEW_WINDOW_LIMIT
                post_message(
                  dialog,
                  'error',
                  format(
                    'Detected %d windows — click false boxes on the image and Delete, then Generate.',
                    window_count
                  )
                )
              elsif door_count.zero?
                post_message(
                  dialog,
                  'success',
                  format(
                    'Detected %d windows, no door (door fields cleared). Review before Generate.',
                    window_count
                  )
                )
              else
                post_message(
                  dialog,
                  'success',
                  format(
                    'Detected %d windows, %d doors (%.2f %s). Review before Generate.',
                    window_count,
                    door_count,
                    result.confidence,
                    result.method
                  )
                )
              end
            end
          rescue GeomoraError => e
            post_message(dialog, 'error', e.message)
          end

          dialog.add_action_callback('load_template') do |_ctx, _|
            data = JSON.parse(File.read(Core::Project.fixture_path))
            dialog.execute_script("window.geomora.loadPayload(#{payload_from_ir(data).to_json}, 'template')")
          end

          dialog.add_action_callback('validate') do |_ctx, json|
            params = enrich_params(JSON.parse(json))
            ir = Core::Project.build_manual_facade(params)
            Core::Project.validate_data(ir)
            post_message(dialog, 'success', 'Validation passed.')
            dialog.execute_script("window.geomora.setIrPreview(#{ir.to_json})")
          rescue GeomoraError => e
            post_message(dialog, 'error', e.message)
          end

          dialog.add_action_callback('generate') do |_ctx, json|
            params = enrich_params(JSON.parse(json))
            windows = params['windows']
            if windows.is_a?(Array) && windows.length > REVIEW_WINDOW_LIMIT
              raise GeomoraError,
                    "Too many windows (#{windows.length}). Delete false boxes on the image (max #{REVIEW_WINDOW_LIMIT}), then Generate again."
            end

            ir = Core::Project.build_manual_facade(params)
            Core::Project.generate_from_data(ir)
            post_message(dialog, 'success', 'Generation complete.')
            dialog.execute_script("window.geomora.setIrPreview(#{ir.to_json})")
          rescue GeomoraError => e
            post_message(dialog, 'error', e.message)
          end
        end

        def enrich_params(params)
          params['rectification'] = @rectification if @rectification
          params['detection'] = @detection if @detection
          params
        end

        def detection_image_path(params)
          return @rectified_image_path if @rectified_image_path && File.exist?(@rectified_image_path)

          params['source_path']
        end

        def save_overlay_from_result(result)
          cache_dir = File.join(Core::Project.plugin_root, 'cache')
          path = File.join(cache_dir, "detect_overlay_#{Time.now.to_i}.jpg")
          require 'base64'
          File.binwrite(path, Base64.decode64(result.overlay_base64))
          path
        end

        def default_payload
          empty_manual_payload
        end

        def empty_manual_payload
          {
            'project_name' => 'Untitled Facade',
            'wall_length' => 10_000,
            'wall_height' => 3300,
            'wall_thickness' => 240,
            'windows' => [],
            'door' => { 'offset' => 0, 'width' => 0, 'height' => 2100 },
            'source_path' => nil,
            'source_id' => nil
          }
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
