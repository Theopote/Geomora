# frozen_string_literal: true

require_relative '../test_helper'

class ViewportSnapshotTest < Minitest::Test
  def test_capture_returns_data_url
    model = Object.new
    model.define_singleton_method(:active_view) { nil }
    snapshot = Geomora::Core::ViewportSnapshot.capture(model)
    assert snapshot['data_url'].start_with?('data:image/png;base64,')
    assert File.exist?(snapshot['path'])
  ensure
    File.delete(snapshot['path']) if defined?(snapshot) && snapshot && snapshot['path'] && File.exist?(snapshot['path'])
  end
end
