# frozen_string_literal: true

require_relative '../test_helper'

class ViewportStreamTest < Minitest::Test
  def test_stop_when_inactive
    Geomora::Core::ViewportStream.stop
    refute Geomora::Core::ViewportStream.active?
  end
end
