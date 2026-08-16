# frozen_string_literal: true

module Geomora
  module Core
    class AviEncoder
      def self.encode(frames, path, fps: 0.5)
        raise GeomoraError, 'No AVI frames to encode' if frames.nil? || frames.empty?

        width = frames.first['width']
        height = frames.first['height']
        fps = fps.to_f.positive? ? fps.to_f : 0.5
        microsec_per_frame = (1_000_000 / fps).round
        bitmaps = frames.map { |frame| bitmap_chunk(frame['rgb'], frame['width'], frame['height']) }
        max_bytes = bitmaps.map(&:bytesize).max

        movi_body = bitmaps.map { |bitmap| chunk('00db', bitmap) }.join
        movi = list('movi', movi_body)
        strf = chunk('strf', bitmap_info_header(width, height))
        strh = chunk('strh', stream_header(width, height, bitmaps.length, microsec_per_frame, max_bytes))
        strl = list('strl', strh + strf)
        avih = chunk('avih', main_header(width, height, bitmaps.length, microsec_per_frame, max_bytes))
        hdrl = list('hdrl', avih + strl)
        idx1 = chunk('idx1', index_entries(bitmaps))
        body = hdrl + movi + idx1
        File.binwrite(path, riff('AVI ', body))
        path
      end

      def self.bitmap_chunk(rgb, width, height)
        bitmap_info_header(width, height) + flip_rows(rgb, width, height)
      end

      def self.bitmap_info_header(width, height)
        [40, width, height * 2, 1, 24, 0, 0, 0, 0, 0, 0].pack('VlSSVVVVVVV')
      end

      def self.flip_rows(rgb, width, height)
        row_bytes = width * 3
        pad = (4 - (row_bytes % 4)) % 4
        out = +''
        (height - 1).downto(0) do |row|
          start = row * row_bytes
          out << rgb.byteslice(start, row_bytes)
          out << ("\0" * pad) if pad.positive?
        end
        out
      end

      def self.main_header(width, height, frame_count, microsec_per_frame, max_bytes)
        [
          microsec_per_frame, max_bytes, 0, 0x10, frame_count, 0, 1, max_bytes,
          width, height, 0, 0, 0, 0
        ].pack('VVVVVVVVVVVVVV')
      end

      def self.stream_header(width, height, frame_count, microsec_per_frame, max_bytes)
        rate = (1_000_000.0 / microsec_per_frame).round
        [
          'vids', 'DIB ', 0,
          0, 0,
          0,
          1, rate,
          0, frame_count,
          max_bytes, 0xFFFFFFFF, 0,
          0, 0, width, height
        ].pack('a4a4VVvvVVVVVVVVvv')
      end

      def self.index_entries(bitmaps)
        offset = 4
        bitmaps.map do |bitmap|
          entry = ['00db', 0x10, offset, bitmap.bytesize].pack('a4VVV')
          offset += 8 + bitmap.bytesize
          entry
        end.join
      end

      def self.list(type, data)
        riff('LIST', type + data)
      end

      def self.chunk(type, data)
        type.ljust(4, "\0")[0, 4] + [data.bytesize].pack('V') + data
      end

      def self.riff(type, data)
        "RIFF" + [data.bytesize + 4].pack('V') + type.ljust(4, "\0")[0, 4] + data
      end
    end
  end
end
