# frozen_string_literal: true

require_relative '../test_helper'
require File.join(PLUGIN, 'core/a1_benchmark')

class A1BenchmarkTest < Minitest::Test
  def setup
    @e2e = Geomora::Core::A1Benchmark.load_e2e
    @manifest = Geomora::Core::A1Benchmark.load_manifest
  end

  def test_queue_orders_holdout_first
    queue = Geomora::Core::A1Benchmark.queue(@e2e['results'])
    assert_equal 'holdout', queue.first['split']
    assert_equal 20, queue.length
  end

  def test_sketchup_action_for_missed_window_and_false_door
    row = @e2e['results'].find { |entry| entry['id'] == 'photo_16' }
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
    assert_equal 20, summary[:total]
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
end
