# frozen_string_literal: true

require_relative '../test_helper'

class PdfReportExporterTest < Minitest::Test
  def test_exports_pdf
    params = {
      'wall_length' => 9000,
      'building_depth' => 6000,
      'partition_count' => 1
    }
    path = File.join(Dir.tmpdir, "geomora_layout_#{Process.pid}.pdf")
    Geomora::Core::PdfReportExporter.export(params, path)
    header = File.read(path, 8)
    assert_equal '%PDF-1.4', header
  ensure
    File.delete(path) if path && File.exist?(path)
  end
end
