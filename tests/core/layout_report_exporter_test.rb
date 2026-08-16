# frozen_string_literal: true

require_relative '../test_helper'

class LayoutReportExporterTest < Minitest::Test
  def test_exports_html_report
    params = {
      'wall_length' => 9000,
      'building_depth' => 6000,
      'partition_count' => 1,
      'storey_count' => 1
    }
    path = File.join(Dir.tmpdir, "geomora_layout_#{Process.pid}.html")
    Geomora::Core::LayoutReportExporter.export_html(params, path)
    html = File.read(path)
    assert_includes html, 'Geomora Layout Report'
    assert_includes html, '<svg'
  ensure
    File.delete(path) if path && File.exist?(path)
  end
end
