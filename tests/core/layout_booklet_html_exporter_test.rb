# frozen_string_literal: true

require_relative '../test_helper'

class LayoutBookletHtmlExporterTest < Minitest::Test
  def test_exports_booklet_html
    params = {
      'wall_length' => 9000,
      'building_depth' => 6000,
      'partition_count' => 1
    }
    path = File.join(Dir.tmpdir, "geomora_booklet_#{Process.pid}.html")
    Geomora::Core::LayoutReportExporter.export_html_booklet(params, path)
    html = File.read(path)
    assert_includes html, 'Geomora Layout Booklet'
    assert_includes html, 'Contents'
    assert_includes html, 'room-card'
  ensure
    File.delete(path) if path && File.exist?(path)
  end
end
