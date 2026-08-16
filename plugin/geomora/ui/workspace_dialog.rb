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
          dialog.set_on_closed { Core::ViewportStream.stop } if dialog.respond_to?(:set_on_closed)
          dialog.set_file(HTML_PATH)
          dialog
        end

        def register_callbacks(dialog)
          dialog.add_action_callback('ready') do |_ctx, _|
            payload = default_payload
            dialog.execute_script("window.geomora.loadPayload(#{payload.to_json})")
          end

          dialog.add_action_callback('pick_secondary_image') do |_ctx, _|
            path = ::UI.openpanel('Select secondary facade image', '', 'Images|*.jpg;*.jpeg;*.png;*.webp;||')
            if path
              @secondary_source_path = path
              file_url = path_to_file_url(path)
              dialog.execute_script(
                "window.geomora.setSecondaryImage(#{file_url.to_json}, #{path.to_json})"
              )
            end
          end

          dialog.add_action_callback('fuse_views') do |_ctx, json|
            params = JSON.parse(json)
            primary_path = fusion_primary_path(params)
            secondary_path = params['secondary_source_path']
            if primary_path.nil? || primary_path.empty?
              raise GeomoraError, 'Load and rectify a primary image first.'
            end
            if secondary_path.nil? || secondary_path.empty?
              raise GeomoraError, 'Load a secondary image before fusing views.'
            end

            homography = params.dig('multiview', 'homography') || params['homography']
            detection_method = params['detection_method'].to_s.strip
            detection_method = 'auto' if detection_method.empty?
            depth_method = params['depth_method'].to_s.strip
            depth_method = 'auto' if depth_method.empty?
            register_method = params['register_method'].to_s.strip
            register_method = 'auto' if register_method.empty?

            Logger.info("Fusing openings: #{primary_path} + #{secondary_path}")
            result = Perception::MultiviewClient.fuse(
              primary_path,
              secondary_path,
              homography: homography,
              method: detection_method,
              depth_method: depth_method,
              register_method: register_method
            )
            @fusion = result.to_source_metadata
            if result.registration
              @multiview = Perception::MultiviewResult.from_hash(result.registration).to_source_metadata
            end

            detection = result.to_detection_result
            mapped = Core::DetectionMapper.to_facade_params(
              detection,
              wall_length: params['wall_length'],
              wall_height: params['wall_height'],
              wall_thickness: params['wall_thickness']
            )
            @detection = detection.to_source_metadata.merge('fusion' => @fusion)

            overlay_url = nil
            if detection.overlay_base64 && !detection.overlay_base64.empty?
              overlay_path = save_overlay_from_result(detection)
              overlay_url = path_to_file_url(overlay_path) if overlay_path
            end

            payload = mapped.merge(
              'detection' => detection.to_dict,
              'fusion' => @fusion
            )
            dialog.execute_script(
              "window.geomora.applyFusion(#{payload.to_json}, #{overlay_url.to_json})"
            )
            post_message(
              dialog,
              'success',
              format(
                'Fused %d openings from two views (%.2f %s)',
                detection.elements.length,
                result.confidence,
                result.method
              )
            )
          rescue GeomoraError => e
            post_message(dialog, 'error', e.message)
          end

          dialog.add_action_callback('register_views') do |_ctx, json|
            params = JSON.parse(json)
            primary_path = params['source_path']
            secondary_path = params['secondary_source_path']
            if primary_path.nil? || primary_path.empty?
              raise GeomoraError, 'Load a primary reference image first.'
            end
            if secondary_path.nil? || secondary_path.empty?
              raise GeomoraError, 'Load a secondary image before registering views.'
            end

            Logger.info("Registering views: #{primary_path} + #{secondary_path}")
            register_method = params['register_method'].to_s.strip
            register_method = 'auto' if register_method.empty?
            result = Perception::MultiviewClient.register(
              primary_path,
              secondary_path,
              method: register_method
            )
            @multiview = result.to_source_metadata
            dialog.execute_script("window.geomora.setMultiviewRegistration(#{result.to_dict.to_json})")
            post_message(
              dialog,
              result.inlier_count >= 20 ? 'success' : '',
              format(
                'Views registered — %d matches, %d inliers (%.2f %s)',
                result.match_count,
                result.inlier_count,
                result.confidence,
                result.method
              )
            )
          rescue GeomoraError => e
            post_message(dialog, 'error', e.message)
          end

          dialog.add_action_callback('pick_image') do |_ctx, _|
            path = ::UI.openpanel('Select facade reference image', '', 'Images|*.jpg;*.jpeg;*.png;*.webp;||')
            if path
              @source_path = path
              file_url = path_to_file_url(path)
              dialog.execute_script("window.geomora.setImage(#{file_url.to_json}, #{path.to_json})")
            end
          end

          dialog.add_action_callback('pick_video') do |_ctx, _|
            path = ::UI.openpanel(
              'Select facade video',
              '',
              'Videos|*.mp4;*.mov;*.avi;*.mkv;*.webm;||'
            )
            next unless path

            data = Perception::VideoFrameClient.extract_frames(path)
            frames = (data['frames'] || []).map do |frame|
              {
                'index' => frame['index'],
                'frame_number' => frame['frame_number'],
                'timestamp_sec' => frame['timestamp_sec'],
                'path' => frame['path'],
                'thumb_url' => frame['thumb_path'] ? path_to_file_url(frame['thumb_path']) : nil
              }
            end
            payload = {
              'video_path' => path,
              'duration_sec' => data['duration_sec'],
              'fps' => data['fps'],
              'frames' => frames
            }
            dialog.execute_script("window.geomora.setVideoFrames(#{payload.to_json})")
            post_message(
              dialog,
              'success',
              format('Extracted %d frames from video. Pick a key frame below.', frames.length)
            )
          rescue GeomoraError => e
            post_message(dialog, 'error', e.message)
          end

          dialog.add_action_callback('load_video_frame') do |_ctx, json|
            payload = JSON.parse(json)
            path = payload['path']
            raise GeomoraError, 'Video frame path missing' if path.nil? || path.empty?

            @source_path = path
            file_url = path_to_file_url(path)
            dialog.execute_script(
              "window.geomora.setImage(#{file_url.to_json}, #{path.to_json}, 'video_frame')"
            )
            post_message(dialog, 'success', 'Video frame loaded as primary image.')
          rescue GeomoraError => e
            post_message(dialog, 'error', e.message)
          end

          dialog.add_action_callback('rectify') do |_ctx, json|
            params = JSON.parse(json)
            source_path = params['source_path']
            if source_path.nil? || source_path.empty?
              raise GeomoraError, 'Load a reference image before rectifying.'
            end

            Logger.info("Rectifying image: #{source_path}")
            corners = params['corners']
            if corners.is_a?(Array) && corners.length == 4
              result = Perception::RectifyClient.rectify(source_path, corners: corners)
            else
              result = Perception::RectifyClient.rectify(source_path)
            end
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

            detection_method = params['detection_method']
            detection_method = detection_method.to_s.strip
            detection_method = 'auto' if detection_method.empty?

            Logger.info("Detecting facade elements: #{image_path} (method=#{detection_method})")
            result = Perception::DetectClient.detect(image_path, method: detection_method)
            params = apply_detection_scale!(params, result)
            mapped = map_detection_params(result, params)

            if openings_empty?(mapped) && contour_fallback?(detection_method)
              Logger.info('Auto/YOLO found no usable openings — retrying with facade_row_v1')
              result = Perception::DetectClient.detect(image_path, method: 'facade_row_v1')
              params = apply_detection_scale!(params, result)
              mapped = map_detection_params(result, params)
            end

            if openings_empty?(mapped) && contour_fallback?(detection_method)
              Logger.info('facade_row_v1 found no usable openings — retrying with contour_v1')
              result = Perception::DetectClient.detect(image_path, method: 'contour_v1')
              params = apply_detection_scale!(params, result)
              mapped = map_detection_params(result, params)
            end

            @detection = result.to_source_metadata
            overlay_url = detection_overlay_url(result)

            if openings_empty?(mapped)
              dialog.execute_script(
                "window.geomora.onDetectionEmpty(#{result.to_dict.to_json}, #{overlay_url.to_json})"
              )
              post_message(
                dialog,
                'warning',
                'No openings detected. Use Overlay → Draw window, or set Detection to Contour and retry.'
              )
            else
              payload = mapped.merge('detection' => result.to_dict)
              payload['scale_hint'] = params['scale_hint'] if params['scale_hint']
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

          dialog.add_action_callback('apply_pattern') do |_ctx, json|
            params = JSON.parse(json)
            if params['windows'].is_a?(Array) && params['windows'].length < 2
              raise GeomoraError, 'Add at least two windows before applying a pattern.'
            end

            result = Core::Project.analyze_pattern(params)
            payload = params.merge(result)
            dialog.execute_script("window.geomora.applyPattern(#{payload.to_json})")
            pattern = result['pattern'] || {}
            post_message(
              dialog,
              'success',
              format(
                'Pattern: %s (%s)',
                pattern['type'] || 'none',
                (pattern['patterns_detected'] || []).join(', ')
              )
            )
          rescue GeomoraError => e
            post_message(dialog, 'error', e.message)
          end

          dialog.add_action_callback('rationalize') do |_ctx, json|
            params = JSON.parse(json)
            if params['windows'].is_a?(Array) && params['windows'].empty?
              raise GeomoraError, 'Add at least one window before rationalizing.'
            end

            result = Core::Project.rationalize_facade(params)
            payload = params.merge(result)
            dialog.execute_script("window.geomora.applyRationalization(#{payload.to_json})")
            applied = result.dig('rationalization', 'constraints_applied') || []
            post_message(
              dialog,
              'success',
              format('Rationalized (%s)', applied.join(', '))
            )
          rescue GeomoraError => e
            post_message(dialog, 'error', e.message)
          end

          dialog.add_action_callback('solve_constraints') do |_ctx, json|
            params = JSON.parse(json)
            if params['windows'].is_a?(Array) && params['windows'].empty?
              raise GeomoraError, 'Add at least one window before solving constraints.'
            end
            constraints = params['constraints']
            if constraints.nil? || !constraints.is_a?(Array) || constraints.empty?
              ir = Core::Project.build_manual_facade(params)
              constraints = ir['constraints'] || []
              params = params.merge('constraints' => constraints)
            end
            if constraints.empty?
              raise GeomoraError, 'No constraints to solve. Rationalize or Apply Pattern first.'
            end

            result = Core::Project.solve_constraints(params)
            payload = params.merge(result)
            dialog.execute_script("window.geomora.applyConstraintSolution(#{payload.to_json})")
            solved = result.dig('constraint_solution', 'constraints_solved') || []
            post_message(
              dialog,
              'success',
              format('Constraints solved (%s)', solved.join(', '))
            )
          rescue GeomoraError => e
            post_message(dialog, 'error', e.message)
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

          dialog.add_action_callback('repair_geometry') do |_ctx, json|
            params = enrich_params(JSON.parse(json))
            openings = params['windows'] || []
            door = params['door'] || {}
            expected_openings = openings.length + (door['width'].to_f.positive? ? 1 : 0)
            doctor_opts = params['geometry_doctor'] || {}
            doctor_opts['expected_openings'] = expected_openings

            report = Core::Project.repair_geometry(doctor_opts)
            post_message(dialog, 'success', format_repair_report(report))
          rescue GeomoraError => e
            post_message(dialog, 'error', e.message)
          end

          dialog.add_action_callback('reload_fixture_catalog') do |_ctx, json|
            params = enrich_params(JSON.parse(json))
            catalog = Core::FixtureCatalog.reload!(params)
            sets = catalog['sets'].is_a?(Hash) ? catalog['sets'].keys : []
            post_message(dialog, 'success', format('Fixture catalog reloaded (%d sets)', sets.length))
          rescue GeomoraError => e
            post_message(dialog, 'error', e.message)
          end

          dialog.add_action_callback('suggest_room_layout') do |_ctx, json|
            params = enrich_params(JSON.parse(json))
            suggestion = Core::RoomLayoutPresets.suggest(params)
            dialog.execute_script("window.geomora.applyRoomLayoutSuggestion(#{suggestion.to_json})")
            post_message(dialog, 'success', 'Room layout presets applied to form.')
          rescue GeomoraError => e
            post_message(dialog, 'error', e.message)
          end

          dialog.add_action_callback('preview_room_layout') do |_ctx, json|
            params = enrich_params(JSON.parse(json))
            storeys = Core::RoomLayoutEditor.preview_all_storeys(params)
            dialog.execute_script("window.geomora.setRoomLayoutPreview(#{storeys.to_json})")
            room_count = storeys.sum { |storey| storey['rooms'].length }
            post_message(dialog, 'success', format('Layout editor loaded (%d storeys, %d rooms).', storeys.length, room_count))
          rescue GeomoraError => e
            post_message(dialog, 'error', e.message)
          end

          dialog.add_action_callback('layout_catalog_palette') do |_ctx, json|
            params = enrich_params(JSON.parse(json))
            palette = Core::FixtureCatalog.palette(params)
            dialog.execute_script("window.geomora.setLayoutCatalogPalette(#{palette.to_json})")
            post_message(dialog, 'success', format('Catalog palette loaded (%d items).', palette.length))
          rescue GeomoraError => e
            post_message(dialog, 'error', e.message)
          end

          dialog.add_action_callback('preview_fixture_catalog_diff') do |_ctx, json|
            params = enrich_params(JSON.parse(json))
            diff = Core::FixtureCatalog.diff(params)
            dialog.execute_script("window.geomora.setCatalogDiffPreview(#{diff.to_json})")
            post_message(dialog, 'success', diff['summary'] || 'Catalog diff ready.')
          rescue GeomoraError => e
            post_message(dialog, 'error', e.message)
          end

          dialog.add_action_callback('refresh_viewport_snapshot') do |_ctx, _json|
            snapshot = Core::ViewportSnapshot.capture
            dialog.execute_script("window.geomora.setViewportSnapshot(#{snapshot.to_json})")
            post_message(dialog, 'success', 'Viewport snapshot refreshed.')
          rescue GeomoraError => e
            post_message(dialog, 'error', e.message)
          end

          dialog.add_action_callback('start_viewport_stream') do |_ctx, json|
            payload = JSON.parse(json || '{}')
            interval = payload['interval'] || 1.0
            Core::ViewportStream.start(dialog, interval: interval)
            post_message(dialog, 'success', format('Viewport stream started (%ss).', interval))
          rescue GeomoraError => e
            post_message(dialog, 'error', e.message)
          end

          dialog.add_action_callback('stop_viewport_stream') do |_ctx, _json|
            Core::ViewportStream.stop
            dialog.execute_script('window.geomora.stopViewportStreamFallback()')
            post_message(dialog, 'success', 'Viewport stream stopped.')
          end

          dialog.add_action_callback('pause_viewport_stream') do |_ctx, _json|
            Core::ViewportStream.pause
            post_message(dialog, 'success', 'Viewport stream paused.')
          end

          dialog.add_action_callback('resume_viewport_stream') do |_ctx, json|
            payload = JSON.parse(json || '{}')
            interval = payload['interval'] || 1.0
            Core::ViewportStream.resume(interval: interval)
            post_message(dialog, 'success', format('Viewport stream resumed (%ss).', interval))
          end

          dialog.add_action_callback('export_layout_report') do |_ctx, json|
            params = enrich_params(JSON.parse(json))
            path = ::UI.savepanel('Export layout report', '', 'geomora_layout_report.html')
            return unless path

            saved = Core::LayoutReportExporter.export_html(params, path)
            post_message(dialog, 'success', "Layout report exported:\n#{saved}")
          rescue GeomoraError => e
            post_message(dialog, 'error', e.message)
          end

          dialog.add_action_callback('export_layout_report_pdf') do |_ctx, json|
            params = enrich_params(JSON.parse(json))
            path = ::UI.savepanel('Export layout report PDF', '', 'geomora_layout_report.pdf')
            return unless path

            saved = Core::LayoutReportExporter.export_pdf(params, path)
            post_message(dialog, 'success', "Layout PDF exported:\n#{saved}")
          rescue GeomoraError => e
            post_message(dialog, 'error', e.message)
          end

          dialog.add_action_callback('export_layout_report_pdf_booklet') do |_ctx, json|
            params = enrich_params(JSON.parse(json))
            path = ::UI.savepanel('Export layout booklet PDF', '', 'geomora_layout_booklet.pdf')
            return unless path

            saved = Core::LayoutReportExporter.export_pdf_booklet(params, path)
            post_message(dialog, 'success', "Layout booklet PDF exported:\n#{saved}")
          rescue GeomoraError => e
            post_message(dialog, 'error', e.message)
          end

          dialog.add_action_callback('export_layout_report_html_booklet') do |_ctx, json|
            params = enrich_params(JSON.parse(json))
            path = ::UI.savepanel('Export layout booklet HTML', '', 'geomora_layout_booklet.html')
            return unless path

            saved = Core::LayoutReportExporter.export_html_booklet(params, path)
            post_message(dialog, 'success', "Layout booklet HTML exported:\n#{saved}")
          rescue GeomoraError => e
            post_message(dialog, 'error', e.message)
          end
        end

        def enrich_params(params)
          params['rectification'] = @rectification if @rectification
          params['detection'] = @detection if @detection
          params['multiview'] = @multiview if @multiview
          params['fusion'] = @fusion if @fusion
          params
        end

        def fusion_primary_path(params)
          return @rectified_image_path if @rectified_image_path && File.exist?(@rectified_image_path)

          params['source_path']
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
            'source_id' => nil,
            'secondary_source_path' => nil,
            'secondary_source_id' => nil
          }
        end

        def payload_from_ir(data)
          storeys = data.dig('buildings', 0, 'storeys') || []
          wall = storeys.dig(0, 'elements', 0, 'geometry') || {}
          openings = data['openings'] || []
          storey_windows = storeys.map do |storey|
            facade_wall = (storey['elements'] || []).find { |element| element['type'] == 'wall' }
            wall_id = facade_wall ? facade_wall['id'] : nil
            openings.select { |opening| opening['type'] == 'window' && opening['parent_id'] == wall_id }.map do |win|
              {
                'offset' => win.dig('geometry', 'offset'),
                'width' => win.dig('geometry', 'width'),
                'height' => win.dig('geometry', 'height'),
                'sill_height' => win.dig('geometry', 'sill_height')
              }
            end
          end
          windows = storey_windows[0] || openings.select { |o| o['type'] == 'window' }.map do |win|
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
            'storey_count' => storeys.length.positive? ? storeys.length : 1,
            'storey_windows' => storey_windows,
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

        def apply_detection_scale!(params, result)
          return params unless auto_scale_enabled?(params)

          hint = result.scale_hint
          if hint.nil? || hint.empty?
            hint = Core::ScaleEstimator.from_detection(
              result.elements,
              image_width: result.image_width,
              image_height: result.image_height
            )
          end
          Core::ScaleEstimator.apply_hint!(params, hint) if hint
          params
        end

        def auto_scale_enabled?(params)
          value = params['auto_scale']
          return true if value.nil?

          !%w[false 0 off no].include?(value.to_s.strip.downcase)
        end

        def map_detection_params(result, params)
          Core::DetectionMapper.to_facade_params(
            result,
            wall_length: params['wall_length'],
            wall_height: params['wall_height'],
            wall_thickness: params['wall_thickness']
          )
        end

        def openings_empty?(mapped)
          mapped['windows'].empty? && mapped.dig('door', 'width').to_f <= 0
        end

        def contour_fallback?(method)
          %w[auto yolo_v1].include?(method.to_s.strip.downcase)
        end

        def detection_overlay_url(result)
          return nil unless result.overlay_base64 && !result.overlay_base64.empty?

          overlay_path = save_overlay_from_result(result)
          path_to_file_url(overlay_path) if overlay_path
        end

        def format_repair_report(report)
          parts = []
          %w[
            tiny_edges_removed tiny_faces_removed coplanar_edges_merged
            duplicate_faces_removed duplicate_instances_removed normals_reversed
            vertices_snapped empty_groups_removed opening_gaps_found
          ].each do |key|
            value = report[key]
            next unless value.is_a?(Numeric) && value.positive?

            parts << "#{key.tr('_', ' ')}: #{value}"
          end

          components = report['components'] || {}
          if components.any?
            parts << "components: #{components.map { |k, v| "#{k}(#{v})" }.join(', ')}"
          end

          parts.empty? ? 'Geometry doctor complete (no changes needed).' : "Geometry doctor: #{parts.join('; ')}"
        end

        def post_message(dialog, level, message)
          dialog.execute_script("window.geomora.setStatus(#{level.to_json}, #{message.to_json})")
        end
      end
    end
  end
end
