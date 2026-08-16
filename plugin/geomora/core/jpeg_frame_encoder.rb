# frozen_string_literal: true

module Geomora
  module Core
    class JpegFrameEncoder
      LUMINANCE_QUANT = [
        16, 11, 10, 16, 24, 40, 51, 61,
        12, 12, 14, 19, 26, 58, 60, 55,
        14, 13, 16, 24, 40, 57, 69, 56,
        14, 17, 22, 29, 51, 87, 80, 62,
        18, 22, 37, 56, 68, 109, 103, 77,
        24, 35, 55, 64, 81, 104, 113, 92,
        49, 64, 78, 87, 103, 121, 120, 101,
        72, 92, 95, 98, 112, 100, 103, 99
      ].freeze

      DC_LUMINANCE_BITS = [0, 1, 5, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0].freeze
      DC_LUMINANCE_VALUES = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11].freeze
      AC_LUMINANCE_BITS = [0, 2, 1, 3, 3, 2, 4, 3, 5, 5, 4, 4, 0, 0, 1, 125].freeze
      AC_LUMINANCE_VALUES = [
        0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06, 0x13, 0x51, 0x61, 0x07,
        0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xA1, 0x08, 0x23, 0x42, 0xB1, 0xC1, 0x15, 0x52, 0xD1, 0xF0,
        0x24, 0x33, 0x62, 0x72, 0x82, 0x09, 0x0A, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x25, 0x26, 0x27, 0x28,
        0x29, 0x2A, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49,
        0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5A, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69,
        0x6A, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79, 0x7A, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89,
        0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7,
        0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6, 0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3, 0xC4, 0xC5,
        0xC6, 0xC7, 0xC8, 0xC9, 0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xE1, 0xE2,
        0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xF1, 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF8,
        0xF9, 0xFA
      ].freeze

      def self.encode_rgb(rgb, width, height)
        blocks = blocks_from_rgb(rgb, width, height)
        bitstream = BitWriter.new
        write_start_of_image(bitstream)
        write_quantization_tables(bitstream)
        write_start_of_frame(bitstream, width, height)
        write_huffman_tables(bitstream)
        write_start_of_scan(bitstream)
        previous_dc = 0
        blocks.each do |y_value|
          dc = ((y_value - 128) / LUMINANCE_QUANT[0]).round
          encode_dc_coefficient(bitstream, dc - previous_dc)
          previous_dc = dc
          bitstream.write_bits(0x00, 4)
          bitstream.write_bits(0x00, 4)
        end
        bitstream.align_byte
        bitstream.write_bytes([0xFF, 0xD9])
        bitstream.bytes
      end

      def self.blocks_from_rgb(rgb, width, height)
        padded_w = ((width + 7) / 8) * 8
        padded_h = ((height + 7) / 8) * 8
        blocks = []
        (0...padded_h).step(8) do |y0|
          (0...padded_w).step(8) do |x0|
            sum = 0.0
            count = 0
            8.times do |dy|
              8.times do |dx|
                x = x0 + dx
                y = y0 + dy
                next if x >= width || y >= height

                base = (y * width + x) * 3
                r = rgb.getbyte(base)
                g = rgb.getbyte(base + 1)
                b = rgb.getbyte(base + 2)
                sum += (0.299 * r) + (0.587 * g) + (0.114 * b)
                count += 1
              end
            end
            blocks << (count.zero? ? 0 : sum / count)
          end
        end
        blocks
      end

      def self.write_start_of_image(bitstream)
        bitstream.write_bytes([0xFF, 0xD8, 0xFF, 0xE0])
        bitstream.write_bytes([0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01, 0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00])
      end

      def self.write_quantization_tables(bitstream)
        bitstream.write_bytes([0xFF, 0xDB, 0x00, 0x43, 0x00])
        bitstream.write_bytes(LUMINANCE_QUANT)
      end

      def self.write_start_of_frame(bitstream, width, height)
        bitstream.write_bytes([0xFF, 0xC0, 0x00, 0x0B, 0x08])
        bitstream.write_bytes([(height >> 8) & 0xFF, height & 0xFF, (width >> 8) & 0xFF, width & 0xFF, 0x01, 0x01, 0x11, 0x00])
      end

      def self.write_huffman_tables(bitstream)
        bitstream.write_bytes([0xFF, 0xC4, 0x00, 0x1F, 0x00])
        bitstream.write_bytes(DC_LUMINANCE_BITS)
        bitstream.write_bytes(DC_LUMINANCE_VALUES)
        bitstream.write_bytes([0xFF, 0xC4, 0x00, 0xB5, 0x10])
        bitstream.write_bytes(AC_LUMINANCE_BITS)
        bitstream.write_bytes(AC_LUMINANCE_VALUES)
      end

      def self.write_start_of_scan(bitstream)
        bitstream.write_bytes([0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F, 0x00])
      end

      def self.encode_dc_coefficient(bitstream, value)
        magnitude = value.abs
        bits_needed = magnitude.zero? ? 0 : Math.log2(magnitude).floor + 1
        bitstream.write_bits(huffman_code(DC_LUMINANCE_BITS, DC_LUMINANCE_VALUES, bits_needed), bits_needed.zero? ? 2 : bits_needed + 1)
        return if magnitude.zero?

        bitstream.write_bits(value.negative? ? (magnitude ^ ((1 << bits_needed) - 1)) : magnitude, bits_needed)
      end

      def self.huffman_code(bits, values, symbol)
        offset = bits[0...symbol].sum
        length = bits[symbol]
        value = 0
        length.times { |index| value = (value << 1) | (values[offset + index] & 1) }
        value
      end

      class BitWriter
        attr_reader :bytes

        def initialize
          @bytes = +''
          @buffer = 0
          @bits = 0
        end

        def write_bits(value, count)
          @buffer = (@buffer << count) | (value & ((1 << count) - 1))
          @bits += count
          while @bits >= 8
            emit_byte((@buffer >> (@bits - 8)) & 0xFF)
            @bits -= 8
          end
        end

        def write_bytes(array)
          align_byte if @bits.positive?
          @bytes << array.pack('C*')
        end

        def align_byte
          return unless @bits.positive?

          emit_byte((@buffer << (8 - @bits)) & 0xFF)
          @buffer = 0
          @bits = 0
        end

        def emit_byte(byte)
          @bytes << byte.chr
          return unless byte == 0xFF

          @bytes << "\x00"
        end
      end
    end
  end
end
