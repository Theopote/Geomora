# frozen_string_literal: true

require_relative '../test_helper'

class H264CavlcTest < Minitest::Test
  def test_h264_compact_smaller_than_ipcm
    frame = Geomora::Core::LodCapture.placeholder_rgb(32, 32)
    compact = Geomora::Core::H264FrameEncoder.encode_idr(
      frame['rgb'], frame['width'], frame['height'],
      Geomora::Core::H264FrameEncoder.configuration(frame['width'], frame['height'])
    )
    ipcm_writer = Geomora::Core::H264Bitstream::Writer.new
    yuv = Geomora::Core::H264FrameEncoder.rgb_to_yuv420(
      Geomora::Core::H264FrameEncoder.pad_rgb(frame['rgb'], frame['width'], frame['height'], 32, 32),
      32, 32
    )
    Geomora::Core::H264FrameEncoder.write_ipcm_macroblock(ipcm_writer, yuv, 32, 0, 0)
    assert_operator compact.bytesize, :<, ipcm_writer.bytes.bytesize
  end
end
