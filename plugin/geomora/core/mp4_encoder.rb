# frozen_string_literal: true

module Geomora
  module Core
    class Mp4Encoder
      def self.encode(frames, path, fps: 0.5)
        raise GeomoraError, 'No MP4 frames to encode' if frames.nil? || frames.empty?

        fps = fps.to_f.positive? ? fps.to_f : 0.5
        samples = frames.map do |frame|
          JpegFrameEncoder.encode_rgb(frame['rgb'], frame['width'], frame['height'])
        end
        timescale = 1000
        sample_delta = (timescale / fps).round
        mdat_body = samples.join
        ftyp = box('ftyp', 'isom' + [0, 0, 0, 1].pack('N') + 'isom' + 'mp41')
        mdat_data_offset = ftyp.bytesize + 8
        moov = build_moov(
          width: frames.first['width'],
          height: frames.first['height'],
          sample_sizes: samples.map(&:bytesize),
          sample_delta: sample_delta,
          timescale: timescale,
          mdat_offset: mdat_data_offset
        )
        mdat = box('mdat', mdat_body)
        File.binwrite(path, ftyp + mdat + moov)
        path
      end

      def self.build_moov(width:, height:, sample_sizes:, sample_delta:, timescale:, mdat_offset:)
        stsd = jpeg_sample_entry(width, height)
        stts = full_box('stts', 0, 0, [sample_sizes.length, sample_delta].pack('NN'))
        stsc = full_box('stsc', 0, 0, [1, sample_sizes.length, 1].pack('NNN'))
        stsz = full_box('stsz', 0, 0, [0, sample_sizes.length].pack('NN') + sample_sizes.pack('N*'))
        chunk_offset = mdat_offset + 8
        stco = full_box('stco', 0, 0, [chunk_offset].pack('N'))
        stbl = box('stbl', stsd + stts + stsc + stsz + stco)
        vmhd = full_box('vmhd', 0, 0, [0, 0, 0, 0, 0, 0].pack('nnnnnn'))
        dref = full_box('dref', 0, 0, [1].pack('N') + box('url ', [0].pack('N')))
        dinf = box('dinf', dref)
        minf = box('minf', vmhd + dinf + stbl)
        hdlr = full_box('hdlr', 0, 0, [0].pack('N') + 'vide' + [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0].pack('C*') + 'Geomora Video' + "\0")
        mdhd = full_box('mdhd', 0, 0, [timescale].pack('N') + [sample_sizes.length * sample_delta].pack('N') + [0, 0].pack('nn'))
        mdia = box('mdia', mdhd + hdlr + minf)
        tkhd = full_box('tkhd', 0, 0, [0, 0].pack('NN') + [1].pack('N') + [0].pack('N') + [sample_sizes.length * sample_delta].pack('N') + [0, 0, 0].pack('NNN') + [0, 0, 0, 0].pack('nnnn') + [width, height].pack('nn') + [0x01_00_00_00].pack('N') + [0, 0, 0, 0, 0, 0, 0, 0, 0, 0].pack('N*'))
        trak = box('trak', tkhd + mdia)
        mvhd = full_box('mvhd', 0, 0, [0, 0].pack('NN') + [timescale].pack('N') + [sample_sizes.length * sample_delta].pack('N') + [1.0].pack('N') + [1.0].pack('N') + [0].pack('n') + [0, 0].pack('nn') + [0, 1, 0].pack('nnn') + [0, 0, 0, 0, 0, 0, 0, 0, 0].pack('N*'))
        box('moov', mvhd + trak)
      end

      def self.jpeg_sample_entry(width, height)
        entry = [
          [0, 0, 0, 0, 1].pack('NNnN'),
          'jpeg',
          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0].pack('C*'),
          width, height,
          [0x00_48_00_00, 0x00_48_00_00, 0, 1].pack('NNnN')
        ].join
        full_box('stsd', 0, 0, [1].pack('N') + entry)
      end

      def self.full_box(type, version, flags, body)
        box(type, [version].pack('C') + [flags].pack('N3') + body)
      end

      def self.box(type, body)
        type.ljust(4, "\0")[0, 4] + [body.bytesize + 8].pack('N') + body
      end
    end
  end
end
