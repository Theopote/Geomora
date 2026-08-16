# frozen_string_literal: true

require_relative '../test_helper'

class ViewportStreamTest < Minitest::Test
  def test_stop_when_inactive
    Geomora::Core::ViewportStream.stop
    refute Geomora::Core::ViewportStream.active?
  end

  def test_pause_and_resume
    dialog = Struct.new(:scripts).new([])
    dialog.define_singleton_method(:execute_script) { |script| scripts << script }
    Geomora::Core::ViewportStream.start(dialog, interval: 0.5)
    Geomora::Core::ViewportStream.pause
    assert Geomora::Core::ViewportStream.paused?
    Geomora::Core::ViewportStream.resume(interval: 0.5)
    refute Geomora::Core::ViewportStream.paused?
  ensure
    Geomora::Core::ViewportStream.stop
  end
end
