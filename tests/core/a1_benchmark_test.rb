# frozen_string_literal: true

require_relative '../test_helper'
require File.join(PLUGIN, 'core/a1_benchmark')

class A1BenchmarkTest < Minitest::Test
  FIXTURE_E2E = File.join(ROOT, 'tests', 'fixtures', 'a1_benchmark_e2e.json')
  FIXTURE_CSV = File.join(ROOT, 'tests', 'fixtures', 'a1_benchmark_checklist.csv')

  def setup
    skip 'Missing A1 benchmark fixture' unless File.exist?(FIXTURE_E2E)

    @e2e = JSON.parse(File.read(FIXTURE_E2E, encoding: 'UTF-8'))
    @manifest = Geomora::Core::A1Benchmark.load_manifest
    @original_e2e_path = Geomora::Core::A1Benchmark.e2e_path
    @original_csv_path = Geomora::Core::A1Benchmark.csv_path
    Geomora::Core::A1Benchmark.define_singleton_method(:e2e_path) { FIXTURE_E2E }
    Geomora::Core::A1Benchmark.define_singleton_method(:csv_path) { FIXTURE_CSV }
  end

  def teardown
    Geomora::Core::A1Benchmark.define_singleton_method(:e2e_path) { @original_e2e_path }
    Geomora::Core::A1Benchmark.define_singleton_method(:csv_path) { @original_csv_path }
  end

  def test_queue_orders_holdout_first
    queue = Geomora::Core::A1Benchmark.queue(@e2e['results'])
    assert_equal 'holdout', queue.first['split']
    assert_equal 3, queue.length
  end

  def test_sketchup_action_for_missed_window_and_false_door
    row = {
      'id' => 'photo_16',
      'split' => 'val',
      'automated_failure_hints' => %w[missed_window false_door],
      'detection' => { 'door_count' => 1 }
    }
    action = Geomora::Core::A1Benchmark.sketchup_action(row)
    assert_match(/删误检门/, action)
    assert_match(/Draw window/, action)
  end

  def test_perspective_path_exists_for_manifest_entry
    row = @e2e['results'].first
    path = Geomora::Core::A1Benchmark.perspective_path(row, @manifest)
    assert File.exist?(path), "Expected perspective image at #{path}"
  end

  def test_progress_summary_reads_csv
    summary = Geomora::Core::A1Benchmark.progress_summary
    assert_equal 3, summary[:total]
    assert_equal 'photo_16', summary[:next_id]
  end

  def test_update_csv_row_writes_reviewed_flag
    csv_path = Geomora::Core::A1Benchmark.csv_path
    backup = File.read(csv_path, encoding: 'UTF-8')
    begin
      Geomora::Core::A1Benchmark.update_csv_row(
        'photo_16',
        {
          'sketchup_reviewed' => 'TRUE',
          'generate_ok' => 'false',
          'failure_classes' => 'missed_window;false_door',
          'notes' => 'unit test'
        }
      )
      rows = Geomora::Core::A1Benchmark.load_csv_rows
      assert Geomora::Core::A1Benchmark.reviewed?(rows['photo_16'])
      assert_equal 'unit test', rows['photo_16']['notes']
    ensure
      File.write(csv_path, backup, encoding: 'UTF-8')
    end
  end

  def test_import_scores_to_e2e_merges_csv
    csv_path = Geomora::Core::A1Benchmark.csv_path
    e2e_path = Geomora::Core::A1Benchmark.e2e_path
    csv_backup = File.read(csv_path, encoding: 'UTF-8')
    e2e_backup = File.read(e2e_path, encoding: 'UTF-8')
    out_path = File.join(ROOT, 'backend', 'cache', 'benchmark_a1_e2e_test_import.json')
    begin
      Geomora::Core::A1Benchmark.update_csv_row(
        'photo_16',
        {
          'sketchup_reviewed' => 'TRUE',
          'generate_ok' => 'true',
          'rqs_total' => '72',
          'rqs_perspective_rectification' => '12',
          'failure_classes' => 'missed_window;false_door',
          'notes' => 'import test'
        }
      )

      result = Geomora::Core::A1Benchmark.import_scores_to_e2e(out: out_path)
      payload = JSON.parse(File.read(out_path, encoding: 'UTF-8'))
      merged = payload['results'].find { |row| row['id'] == 'photo_16' }

      assert_equal 3, result[:total]
      assert_equal 1, result[:summary]['reviewed']
      assert_equal '1/1', result[:summary]['holdout_generate_ok']
      assert merged.dig('e2e', 'sketchup_reviewed')
      assert_equal true, merged.dig('e2e', 'generate_ok')
      assert_equal 72, merged.dig('e2e', 'rqs_total')
      assert_includes merged.dig('e2e', 'failure_classes'), 'missed_window'
    ensure
      File.write(csv_path, csv_backup, encoding: 'UTF-8')
      File.write(e2e_path, e2e_backup, encoding: 'UTF-8')
      File.delete(out_path) if File.exist?(out_path)
    end
  end
end
