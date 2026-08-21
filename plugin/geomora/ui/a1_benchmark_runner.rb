# frozen_string_literal: true

module Geomora
  module AppUI
    module A1BenchmarkRunner
      class << self
        def review_next
          entry = Core::A1Benchmark.next_unreviewed
          if entry.nil?
            summary = Core::A1Benchmark.progress_summary
            ::UI.messagebox(
              "A1 benchmark complete.\n\n" \
              "Reviewed: #{summary[:reviewed]}/#{summary[:total]}\n" \
              "Generate OK: #{summary[:generate_ok]}\n" \
              "Hold-out Generate OK: #{summary[:holdout_generate_ok]}"
            )
            return
          end

          @current_entry = entry
          action = Core::A1Benchmark.sketchup_action(entry)
          perspective = Core::A1Benchmark.perspective_path(entry)
          brief = Core::A1Benchmark.format_entry_brief(entry)

          ::UI.messagebox(
            "A1 · Review next\n\n" \
            "#{brief}\n\n" \
            "SketchUp 动作:\n#{action}\n\n" \
            "流程: Load → Rectify → Detect → Overlay → Scale → Rationalize → Validate → Generate\n\n" \
            "完成后用「Record A1 Score」记录分数。"
          )

          WorkspaceDialog.load_a1_photo(perspective, entry['id'], action)
        rescue GeomoraError => e
          ::UI.messagebox("A1 review failed:\n\n#{e.message}")
        end

        def record_score
          entry = @current_entry || Core::A1Benchmark.next_unreviewed
          if entry.nil?
            ::UI.messagebox('No pending A1 photo. All entries are marked reviewed.')
            return
          end

          photo_id = entry['id']
          detect = entry['detection'] || {}
          defaults = Core::A1Benchmark.load_csv_rows[photo_id] || {}

          prompts = [
            'Rectify OK? (true/false)',
            'True window count',
            'True door count',
            'Overlay correction (none/light/medium/heavy)',
            'Generate OK? (true/false)',
            'Correction time (seconds)',
            'Failure classes (semicolon-separated)',
            'RQS total (/100)',
            'Notes'
          ]
          defaults_list = [
            defaults['rectify_ok'].to_s.empty? ? 'true' : defaults['rectify_ok'],
            defaults['windows_true'].to_s.empty? ? detect['window_count'].to_s : defaults['windows_true'],
            defaults['doors_true'].to_s.empty? ? detect['door_count'].to_s : defaults['doors_true'],
            defaults['overlay_correction'].to_s.empty? ? 'light' : defaults['overlay_correction'],
            defaults['generate_ok'].to_s.empty? ? 'true' : defaults['generate_ok'],
            defaults['correction_time_sec'].to_s.empty? ? '60' : defaults['correction_time_sec'],
            defaults['failure_classes'].to_s,
            defaults['rqs_total'].to_s,
            defaults['notes'].to_s
          ]

          input = ::UI.inputbox(prompts, defaults_list, "A1 Score — #{photo_id}")
          return unless input

          Core::A1Benchmark.update_csv_row(
            photo_id,
            {
              'sketchup_reviewed' => 'TRUE',
              'rectify_ok' => input[0],
              'windows_true' => input[1],
              'doors_true' => input[2],
              'overlay_correction' => input[3],
              'generate_ok' => input[4],
              'correction_time_sec' => input[5],
              'failure_classes' => input[6],
              'rqs_total' => input[7],
              'notes' => input[8]
            }
          )

          @current_entry = nil
          summary = Core::A1Benchmark.progress_summary
          ::UI.messagebox(
            "Saved score for #{photo_id}.\n\n" \
            "Progress: #{summary[:reviewed]}/#{summary[:total]} reviewed\n" \
            "Generate OK: #{summary[:generate_ok]}\n" \
            "Hold-out: #{summary[:holdout_generate_ok]}\n\n" \
            "Next: #{summary[:next_id] || 'done — use Import A1 Scores to JSON'}"
          )
        rescue GeomoraError => e
          ::UI.messagebox("A1 score save failed:\n\n#{e.message}")
        end

        def show_progress
          summary = Core::A1Benchmark.progress_summary
          next_entry = Core::A1Benchmark.next_unreviewed
          next_line = if next_entry
                        "#{Core::A1Benchmark.format_entry_brief(next_entry)}\n" \
                          "Action: #{Core::A1Benchmark.sketchup_action(next_entry)}"
                      else
                        'All photos reviewed.'
                      end

          ::UI.messagebox(
            "A1 Real Photo Benchmark\n\n" \
            "Reviewed: #{summary[:reviewed]}/#{summary[:total]}\n" \
            "Generate OK: #{summary[:generate_ok]}\n" \
            "Hold-out Generate OK: #{summary[:holdout_generate_ok]} (gate ≥4/5)\n\n" \
            "Next:\n#{next_line}\n\n" \
            "CSV: #{Core::A1Benchmark.csv_path}"
          )
        rescue GeomoraError => e
          ::UI.messagebox("A1 progress failed:\n\n#{e.message}")
        end

        def open_checklist
          path = Core::A1Benchmark.checklist_html_path
          raise GeomoraError, "Checklist HTML not found: #{path}" unless File.exist?(path)

          ::UI.openURL("file:///#{path.gsub('\\', '/')}")
        rescue GeomoraError => e
          ::UI.messagebox("Open checklist failed:\n\n#{e.message}")
        end

        def open_scores_csv
          path = Core::A1Benchmark.csv_path
          raise GeomoraError, "Checklist CSV not found: #{path}" unless File.exist?(path)

          if RUBY_PLATFORM =~ /mswin|mingw|cygwin/
            system('explorer', "/select,#{path.tr('/', '\\')}")
          else
            ::UI.openURL("file:///#{path.gsub('\\', '/')}")
          end
        rescue GeomoraError => e
          ::UI.messagebox("Open CSV failed:\n\n#{e.message}")
        end

        def import_scores
          result = Core::A1Benchmark.import_scores_to_e2e
          summary = result[:summary]
          message = [
            "Merged #{result[:merged]}/#{result[:total]} rows",
            "Reviewed: #{summary['reviewed']}/#{summary['total']}",
            "Generate OK: #{summary['generate_ok']}",
            "Hold-out Generate OK: #{summary['holdout_generate_ok']} (gate ≥4/5)",
            summary['rqs_avg'] ? "RQS average: #{summary['rqs_avg']}/100" : nil,
            '',
            result[:out_path]
          ].compact.join("\n")

          ::UI.messagebox("A1 scores imported.\n\n#{message}")
          Logger.info("A1 scores imported: #{message.gsub("\n", ' | ')}")
        rescue GeomoraError => e
          ::UI.messagebox("A1 import failed:\n\n#{e.message}")
        end
      end
    end
  end
end
