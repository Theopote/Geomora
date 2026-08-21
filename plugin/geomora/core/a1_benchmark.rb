# frozen_string_literal: true

require 'csv'
require 'json'
require 'set'

module Geomora
  module Core
    class A1Benchmark
      SPLIT_ORDER = { 'holdout' => 0, 'val' => 1, 'train' => 2 }.freeze
      HINT_RANK = {
        'missed_window' => 0,
        'false_door' => 1,
        'false_window' => 2,
        'opening_detection' => 3,
        'bad_rectify' => 4,
        'none' => 9
      }.freeze

      RQS_KEYS = %w[
        perspective_rectification opening_detection opening_placement scale
        pattern_rationalization geometry_validity sketchup_editability human_correction_cost
      ].freeze

      class << self
        def repo_root
          @repo_root ||= File.expand_path('../../..', __dir__)
        end

        def manifest_path
          File.join(repo_root, 'examples', 'real_photos', 'benchmark', 'manifest.json')
        end

        def e2e_path
          File.join(repo_root, 'backend', 'cache', 'benchmark_a1_e2e.json')
        end

        def csv_path
          File.join(repo_root, 'backend', 'cache', 'benchmark_a1', 'checklist_scores.csv')
        end

        def checklist_html_path
          File.join(repo_root, 'backend', 'cache', 'benchmark_a1', 'index.html')
        end

        def load_e2e
          raise GeomoraError, "A1 E2E JSON not found: #{e2e_path}" unless File.exist?(e2e_path)

          JSON.parse(File.read(e2e_path, encoding: 'UTF-8'))
        end

        def load_manifest
          raise GeomoraError, "A1 manifest not found: #{manifest_path}" unless File.exist?(manifest_path)

          JSON.parse(File.read(manifest_path, encoding: 'UTF-8'))
        end

        def queue(results = nil)
          rows = results || load_e2e.fetch('results')
          rows.sort_by { |row| priority_key(row) }
        end

        def priority_key(row)
          hints = row['automated_failure_hints'] || ['none']
          worst_hint = hints.min_by { |hint| HINT_RANK.fetch(hint, 8) }
          detect = row['detection'] || {}
          [
            SPLIT_ORDER.fetch(row['split'], 9),
            HINT_RANK.fetch(worst_hint, 8),
            detect['passed_smoke'] ? 1 : 0,
            detect['confidence'].to_f,
            row['id']
          ]
        end

        def sketchup_action(row)
          hints = (row['automated_failure_hints'] || []).to_set
          split = row['split']
          detect = row['detection'] || {}
          rectify = row['rectify'] || {}

          if hints.include?('missed_window') && detect['door_count'].to_i.positive?
            return '删误检门 + Draw window 补漏检'
          end
          return 'Overlay Draw window 补漏检' if hints.include?('missed_window')
          return 'Delete 多余窗框，核对真实窗数' if hints.include?('false_window')
          return 'Delete 误检门，door width=0' if hints.include?('false_door')
          if hints.include?('bad_rectify') || rectify['method'] == 'auto_full_frame'
            return '手拖四角 Rectify 后再 Detect'
          end
          return '核对每框 + Export train（仅 train split）' if hints.include?('opening_detection')
          return '完整 E2E → 记录 RQS（禁止 Export train）' if split == 'holdout'
          return '完整 E2E → 记录 RQS' if split == 'val'

          '快速目视 → Rationalize → Generate → Export train'
        end

        def perspective_path(row, manifest = nil)
          manifest ||= load_manifest
          root = manifest['perspective_root'] || 'backend/cache/real_photo_desktop_src'
          resolve_image_path(root, row['file'])
        end

        def rectified_path(row, manifest = nil)
          manifest ||= load_manifest
          root = manifest['image_root'] || 'backend/cache/real_photo_desktop_rectified'
          resolve_image_path(root, row['file'])
        end

        def resolve_image_path(root, file_name)
          candidates = [
            File.join(repo_root, root, file_name),
            File.join(repo_root, 'backend', 'cache', 'real_photo_desktop_src', file_name),
            File.join(repo_root, 'backend', 'cache', 'real_photo_desktop_rectified', file_name)
          ]
          found = candidates.find { |path| File.exist?(path) }
          raise GeomoraError, "Image not found: #{file_name}" unless found

          found
        end

        def load_csv_rows
          return {} unless File.exist?(csv_path)

          rows = {}
          CSV.foreach(csv_path, headers: true, encoding: 'bom|utf-8') do |row|
            rows[row['id']] = row.to_h
          end
          rows
        end

        def csv_fields
          base = %w[
            id split category file sketchup_reviewed rectify_ok windows_detected windows_true
            doors_detected doors_true overlay_correction generate_ok correction_time_sec
            failure_classes rqs_total notes
          ]
          base + RQS_KEYS.map { |key| "rqs_#{key}" }
        end

        def reviewed?(csv_row)
          truthy?(csv_row&.fetch('sketchup_reviewed', nil))
        end

        def next_unreviewed
          csv_rows = load_csv_rows
          queue.find { |row| !reviewed?(csv_rows[row['id']]) }
        end

        def progress_summary
          csv_rows = load_csv_rows
          ordered = queue
          reviewed = ordered.count { |row| reviewed?(csv_rows[row['id']]) }
          generate_ok = ordered.count do |row|
            truthy?(csv_rows.dig(row['id'], 'generate_ok'))
          end
          holdout = ordered.select { |row| row['split'] == 'holdout' }
          holdout_ok = holdout.count do |row|
            truthy?(csv_rows.dig(row['id'], 'generate_ok'))
          end

          {
            reviewed: reviewed,
            total: ordered.length,
            generate_ok: generate_ok,
            holdout_generate_ok: "#{holdout_ok}/#{holdout.length}",
            next_id: next_unreviewed&.fetch('id', nil)
          }
        end

        def update_csv_row(photo_id, updates)
          raise GeomoraError, "Checklist CSV not found: #{csv_path}" unless File.exist?(csv_path)

          rows = CSV.read(csv_path, headers: true, encoding: 'bom|utf-8')
          fields = rows.headers
          target = rows.find { |row| row['id'] == photo_id }
          raise GeomoraError, "Photo not in checklist CSV: #{photo_id}" unless target

          updates.each do |key, value|
            next if value.nil?

            target[key] = value.to_s
          end

          if updates.key?(:rqs) && updates[:rqs].is_a?(Hash)
            total = 0
            updates[:rqs].each do |key, score|
              column = "rqs_#{key}"
              next unless fields.include?(column)

              target[column] = score.to_s
              total += score.to_i
            end
            target['rqs_total'] = total.to_s if total.positive?
          end

          CSV.open(csv_path, 'w', encoding: 'UTF-8', write_headers: true, headers: fields) do |csv|
            rows.each { |row| csv << row }
          end
        end

        def format_entry_brief(row)
          detect = row['detection'] || {}
          format(
            '%s [%s] %s — %dw/%dd conf %.2f',
            row['id'],
            row['split'],
            row['category'],
            detect['window_count'].to_i,
            detect['door_count'].to_i,
            detect['confidence'].to_f
          )
        end

        def import_scores_to_e2e(csv: csv_path, e2e: e2e_path, out: nil)
          raise GeomoraError, "Checklist CSV not found: #{csv}" unless File.exist?(csv)
          raise GeomoraError, "A1 E2E JSON not found: #{e2e}" unless File.exist?(e2e)

          payload = JSON.parse(File.read(e2e, encoding: 'UTF-8'))
          csv_rows = load_csv_rows_from(csv)
          rqs_keys = payload.fetch('rqs_rubric', {}).keys
          rqs_keys = RQS_KEYS if rqs_keys.empty?

          merged = 0
          payload['results'].each do |result|
            csv_row = csv_rows[result['id']]
            next unless csv_row

            apply_csv_row_to_e2e!(result, csv_row, rqs_keys)
            merged += 1
          end

          payload['e2e_summary'] = summarize_e2e(payload['results'])
          out_path = out || e2e
          File.write(out_path, JSON.pretty_generate(payload) + "\n", encoding: 'UTF-8')

          {
            merged: merged,
            total: payload['results'].length,
            out_path: out_path,
            summary: payload['e2e_summary']
          }
        end

        def load_csv_rows_from(path)
          rows = {}
          CSV.foreach(path, headers: true, encoding: 'bom|utf-8') do |row|
            rows[row['id']] = row.to_h
          end
          rows
        end

        def apply_csv_row_to_e2e!(result, csv_row, rqs_keys)
          e2e = result['e2e'] ||= {}
          e2e['sketchup_reviewed'] = truthy?(csv_row['sketchup_reviewed'])

          rectify_ok = csv_row['rectify_ok'].to_s.strip
          if !rectify_ok.empty?
            e2e['rectify_ok'] = boolish?(rectify_ok) ? truthy?(rectify_ok) : rectify_ok
          end

          %w[windows_true doors_true overlay_correction notes].each do |field|
            val = csv_row[field].to_s.strip
            e2e[field] = val unless val.empty?
          end

          generate_ok = csv_row['generate_ok'].to_s.strip
          if !generate_ok.empty?
            lowered = generate_ok.downcase
            e2e['generate_ok'] = if %w[true false 1 0 yes no].include?(lowered)
                                   truthy?(generate_ok)
                                 else
                                   generate_ok
                                 end
          end

          correction_time = csv_row['correction_time_sec'].to_s.strip
          e2e['correction_time_sec'] = parse_optional_float(correction_time) unless correction_time.empty?

          failure = csv_row['failure_classes'].to_s.strip
          unless failure.empty?
            e2e['failure_classes'] = failure.split(/[;,]/).map(&:strip).reject(&:empty?)
          end

          rqs = e2e['rqs'] ||= {}
          rqs_keys.each do |key|
            col = "rqs_#{key}"
            val = csv_row[col].to_s.strip
            rqs[key] = parse_optional_int(val) unless val.empty?
          end

          rqs_total = csv_row['rqs_total'].to_s.strip
          if !rqs_total.empty?
            e2e['rqs_total'] = parse_optional_int(rqs_total)
          elsif rqs_keys.any? { |key| rqs[key].is_a?(Integer) }
            e2e['rqs_total'] = rqs.values.select { |v| v.is_a?(Integer) }.sum
          end
        end

        def summarize_e2e(results)
          reviewed = results.select { |row| row.dig('e2e', 'sketchup_reviewed') }
          generate_ok = reviewed.select { |row| row.dig('e2e', 'generate_ok') == true }
          holdout = results.select { |row| row['split'] == 'holdout' }
          holdout_ok = holdout.select { |row| row.dig('e2e', 'generate_ok') == true }
          rqs_scores = reviewed.filter_map { |row| row.dig('e2e', 'rqs_total') }.select { |v| v.is_a?(Integer) }

          {
            'reviewed' => reviewed.length,
            'total' => results.length,
            'generate_ok' => generate_ok.length,
            'holdout_generate_ok' => "#{holdout_ok.length}/#{holdout.length}",
            'rqs_avg' => rqs_scores.empty? ? nil : (rqs_scores.sum.to_f / rqs_scores.length).round(1)
          }
        end

        private

        def boolish?(value)
          %w[true false 1 0 yes no].include?(value.to_s.strip.downcase)
        end

        def parse_optional_int(value)
          text = value.to_s.strip
          return nil if text.empty?

          text.include?('.') ? text.to_f.to_i : text.to_i
        end

        def parse_optional_float(value)
          text = value.to_s.strip
          return nil if text.empty?

          text.to_f
        end

        def truthy?(value)
          %w[true 1 yes y].include?(value.to_s.strip.downcase)
        end
      end
    end
  end
end
