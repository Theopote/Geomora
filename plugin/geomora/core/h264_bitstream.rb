# frozen_string_literal: true

module Geomora
  module Core
    class H264Bitstream
      class Writer
        attr_reader :bytes

        def initialize
          @bytes = +''
          @buffer = 0
          @bits = 0
          @zeros = 0
        end

        def write_bits(value, count)
          count.times do |index|
            bit = (value >> (count - index - 1)) & 1
            write_bit(bit)
          end
        end

        def write_bit(bit)
          @buffer = (@buffer << 1) | bit
          @bits += 1
          return unless @bits == 8

          emit_byte(@buffer)
          @buffer = 0
          @bits = 0
        end

        def write_ue(value)
          value = value.to_i
          value += 1
          bits = value.to_s(2).length
          write_bits(0, bits - 1)
          write_bits(value, bits)
        end

        def write_se(value)
          mapped = value <= 0 ? (-value * 2) : (value * 2 - 1)
          write_ue(mapped)
        end

        def write_bytes(array)
          align_byte
          @bytes << array.pack('C*')
        end

        def align_byte
          return unless @bits.positive?

          write_bits(0, 8 - @bits)
        end

        def emit_byte(byte)
          if byte == 0
            @zeros += 1
          elsif byte == 3 && @zeros >= 2
            @bytes << "\x00\x03"
            @zeros = 0
            @bytes << byte.chr
          else
            @zeros = 0
            @bytes << byte.chr
          end
        end
      end

      def self.nal_unit(type, body)
        header = [(type & 0x1F) | 0x60].pack('C')
        [0x00, 0x00, 0x00, 0x01].pack('C*') + header + body
      end
    end
  end
end
