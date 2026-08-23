# frozen_string_literal: true

module Geomora
  module Core
    class H264Mp4Encoder
      def self.encode(frames, path, fps: 0.5)
        raise GeomoraError, 'No H.264 frames to encode' if frames.nil? || frames.empty?

        fps = fps.to_f.positive? ? fps.to_f : 0.5
        width = H264FrameEncoder.align16(frames.first['width'])
        height = H264FrameEncoder.align16(frames.first['height'])
        config = H264FrameEncoder.configuration(frames.first['width'], frames.first['height'])
        sps = config['sps']
        pps = config['pps']
        samples = frames.map do |frame|
          nal = H264FrameEncoder.encode_idr(frame['rgb'], frame['width'], frame['height'], config)
          strip_start_code(nal)
        end
        sample_sizes = samples.map(&:bytesize)
        timescale = 1000
        sample_delta = (timescale / fps).round
        mdat_body = samples.map { |sample| [sample.bytesize].pack('N') + sample }.join
        ftyp = box('ftyp', 'isom' + [0, 0, 0, 1].pack('N') + 'isom' + 'avc1')
        mdat_data_offset = ftyp.bytesize + 8
        moov = build_moov(
          width: width,
          height: height,
          sps: sps,
          pps: pps,
          sample_sizes: sample_sizes,
          sample_delta: sample_delta,
          timescale: timescale,
          mdat_offset: mdat_data_offset
        )
        mdat = box('mdat', mdat_body)
        File.binwrite(path, ftyp + mdat + moov)
        path
      end

      def self.strip_start_code(nal)
        bytes = nal.dup
        bytes = bytes.byteslice(4, bytes.bytesize - 4) while bytes.bytesize >= 4 && bytes[0, 4] == "\x00\x00\x00\x01"
        bytes
      end

      def self.build_moov(width:, height:, sps:, pps:, sample_sizes:, sample_delta:, timescale:, mdat_offset:)
        stsd = avc1_sample_entry(width, height, sps, pps)
        stts = full_box('stts', 0, 0, [sample_sizes.length, sample_delta].pack('NN'))
        stsc = full_box('stsc', 0, 0, [1, sample_sizes.length, 1].pack('NNN'))
        stsz = full_box('stsz', 0, 0, [0, sample_sizes.length].pack('NN') + sample_sizes.pack('N*'))
        chunk_offset = mdat_offset + 8
        stco = full_box('stco', 0, 0, [chunk_offset].pack('N'))
        stss = full_box('stss', 0, 0, [sample_sizes.length].pack('N') + (1..sample_sizes.length).to_a.pack('N*'))
        stbl = box('stbl', stsd + stts + stsc + stsz + stco + stss)
        vmhd = full_box('vmhd', 0, 0, [0, 0, 0, 0, 0, 0].pack('nnnnnn'))
        dref = full_box('dref', 0, 0, [1].pack('N') + box('url ', [0].pack('N')))
        dinf = box('dinf', dref)
        minf = box('minf', vmhd + dinf + stbl)
        hdlr = full_box('hdlr', 0, 0, [0].pack('N') + 'vide' + [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0].pack('C*') + 'Geomora H264' + "\0")
        mdhd = full_box('mdhd', 0, 0, [timescale].pack('N') + [sample_sizes.length * sample_delta].pack('N') + [0, 0].pack('nn'))
        mdia = box('mdia', mdhd + hdlr + minf)
        tkhd = full_box('tkhd', 0, 0, [0, 0].pack('NN') + [1].pack('N') + [0].pack('N') + [sample_sizes.length * sample_delta].pack('N') + [0, 0, 0].pack('NNN') + [0, 0, 0, 0].pack('nnnn') + [width, height].pack('nn') + [0x01_00_00_00].pack('N') + [0, 0, 0, 0, 0, 0, 0, 0, 0, 0].pack('N*'))
        trak = box('trak', tkhd + mdia)
        mvhd = full_box('mvhd', 0, 0, [0, 0].pack('NN') + [timescale].pack('N') + [sample_sizes.length * sample_delta].pack('N') + [1.0].pack('N') + [1.0].pack('N') + [0].pack('n') + [0, 0].pack('nn') + [0, 1, 0].pack('nnn') + [0, 0, 0, 0, 0, 0, 0, 0, 0].pack('N*'))
        box('moov', mvhd + trak)
      end

      def self.avc1_sample_entry(width, height, sps, pps)
        sps = sps.b
        pps = pps.b
        avcc = ([1, H264FrameEncoder::PROFILE_BASELINE, 0, H264FrameEncoder::LEVEL_3, 0xFF,
                 0xE1, sps.bytesize].pack('CCCCCCn') + sps + [1, pps.bytesize].pack('Cn') + pps).b
        entry = [
          [0, 0, 0, 0, 1].pack('NNnN'),
          'avc1',
          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0].pack('C*'),
          width, height,
          [0x00_48_00_00, 0x00_48_00_00, 0, 1].pack('NNnN'),
          [0x18].pack('C') + "\xFF\xFF".b,
          box('avcC', avcc)
        ].join.b
        full_box('stsd', 0, 0, [1].pack('N') + entry)
      end

      PROFILE_BASELINE = H264FrameEncoder::PROFILE_BASELINE
      LEVEL_3 = H264FrameEncoder::LEVEL_3

      def self.full_box(type, version, flags, body)
        box(type, [version].pack('C') + [flags, 0, 0].pack('N*') + body)
      end

      def self.box(type, body)
        [body.bytesize + 8].pack('N') + type.ljust(4, "\0")[0, 4] + body
      end
    end
  end
end
