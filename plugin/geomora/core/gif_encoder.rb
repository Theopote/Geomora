# frozen_string_literal: true

require 'stringio'

module Geomora
  module Core
    class GifEncoder
      PALETTE = build_palette.freeze

      def self.encode(frames, path, delay_centiseconds: 20, loop_count: 0)
        raise GeomoraError, 'No GIF frames to encode' if frames.nil? || frames.empty?

        width = frames.first['width']
        height = frames.first['height']
        io = StringIO.new
        io.write('GIF89a')
        io.write([width, height].pack('vv'))
        io.write([0xF7, 0x00, 0x00].pack('CCC'))
        PALETTE.each { |color| io.write(color.pack('CCC')) }
        io.write([0x21, 0xFF, 0x0B].pack('CCC'))
        io.write('NETSCAPE2.0')
        io.write([0x03, 0x01, loop_count, 0x00].pack('CCv'))

        frames.each do |frame|
          indexed = quantize(frame['rgb'], frame['width'], frame['height'])
          io.write([0x21, 0xF9, 0x04, 0x00, delay_centiseconds, 0x00, 0x00].pack('CCCCvC'))
          io.write([0x2C, 0x00, 0x00, 0x00, 0x00, width, height, 0x00].pack('CvvvvC'))
          io.write(lzw_image(indexed, 8))
        end
        io.write(';')
        File.binwrite(path, io.string)
        path
      end

      def self.build_palette
        colors = []
        steps = [0, 51, 102, 153, 204, 255]
        steps.each do |r|
          steps.each do |g|
            steps.each do |b|
              colors << [r, g, b]
            end
          end
        end
        colors.take(256)
      end

      def self.quantize(rgb, width, height)
        pixels = width * height
        indexed = +''
        pixels.times do |index|
          base = index * 3
          indexed << nearest_index(rgb.getbyte(base), rgb.getbyte(base + 1), rgb.getbyte(base + 2)).chr
        end
        indexed
      end

      def self.nearest_index(r, g, b)
        best = 0
        best_dist = Float::INFINITY
        PALETTE.each_with_index do |color, index|
          dr = r - color[0]
          dg = g - color[1]
          db = b - color[2]
          dist = (dr * dr) + (dg * dg) + (db * db)
          next unless dist < best_dist

          best = index
          best_dist = dist
        end
        best
      end

      def self.lzw_image(indexed, min_code_size)
        clear_code = 1 << min_code_size
        end_code = clear_code + 1
        dict = {}
        (0...clear_code).each { |i| dict[i.chr] = i }
        next_code = end_code + 1
        code_size = min_code_size + 1
        codes = [clear_code]
        current = +''

        indexed.each_byte do |byte|
          piece = byte.chr
          candidate = current + piece
          if dict.key?(candidate)
            current = candidate
          else
            codes << dict[current]
            dict[candidate] = next_code
            next_code += 1
            if next_code == (1 << code_size) && code_size < 12
              code_size += 1
            end
            current = piece
          end
        end
        codes << dict[current] unless current.empty?
        codes << end_code

        packed = pack_codes(codes, min_code_size)
        blocks = StringIO.new
        blocks.write(min_code_size.chr)
        packed.bytes.each_slice(255) do |slice|
          block = slice.pack('C*')
          blocks.write(block.bytesize.chr)
          blocks.write(block)
        end
        blocks.write(0.chr)
        blocks.string
      end

      def self.pack_codes(codes, min_code_size)
        clear_code = 1 << min_code_size
        end_code = clear_code + 1
        next_code = end_code + 1
        code_size = min_code_size + 1
        buffer = 0
        bits = 0
        out = +''

        codes.each do |code|
          buffer |= code << bits
          bits += code_size
          while bits >= 8
            out << (buffer & 0xFF).chr
            buffer >>= 8
            bits -= 8
          end
          next_code += 1
          code_size += 1 if next_code == (1 << code_size) && code_size < 12
        end
        out << (buffer & 0xFF).chr if bits.positive?
        out
      end
    end
  end
end
