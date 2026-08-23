# frozen_string_literal: true

module Geomora
  module Core
    class H264Cavlc
      COEFF_TOKEN = {
        0 => {
          0 => { 0 => 1, 1 => [0, 1] },
          1 => { 0 => [0, 0, 1, 1], 1 => [0, 0, 0, 1, 1, 1] }
        },
        2 => {
          0 => { 0 => 1, 1 => [0, 1] },
          1 => { 0 => [0, 0, 0, 1, 1], 1 => [0, 0, 0, 0, 1, 1, 1] }
        }
      }.freeze

      TOTAL_ZEROS = {
        0 => { 0 => 1, 1 => [1, 1, 0] },
        1 => { 0 => [1, 1, 1], 1 => [0, 0, 0, 1, 1] }
      }.freeze

      def self.encode_intra16x16_residual(writer, luma_dcs, cb_dcs, cr_dcs, qp: 26)
        luma_coeffs = hadamard4x4(luma_dcs)
        cb_coeffs = hadamard4x4(cb_dcs)
        cr_coeffs = hadamard4x4(cr_dcs)
        quantize = lambda do |value|
          q = ((value + (value.negative? ? -qp / 2 : qp / 2)) / qp).round
          q.zero? ? 0 : q
        end
        luma_q = luma_coeffs.map { |value| quantize.call(value) }
        cb_q = cb_coeffs.map { |value| quantize.call(value) }
        cr_q = cr_coeffs.map { |value| quantize.call(value) }

        encode_luma_dc_block(writer, luma_q)
        encode_chroma_dc_block(writer, cb_q)
        encode_chroma_dc_block(writer, cr_q)
      end

      def self.encode_luma_dc_block(writer, coeffs)
        encode_block(writer, coeffs, 0, 0)
      end

      def self.encode_chroma_dc_block(writer, coeffs)
        encode_block(writer, coeffs, 0, 0)
      end

      def self.encode_block(writer, coeffs, n_a, n_b)
        nz = coeffs.each_with_index.select { |value, _| !value.zero? }
        total = nz.length
        trailing = [total, 1].min
        write_codeword(writer, lookup_coeff_token(n_a + n_b, total, trailing))
        return if total.zero?

        levels = nz.map(&:first)
        encode_levels(writer, levels, trailing)
        encode_total_zeros(writer, total, coeffs.length - nz.last[1] - 1) if total.positive? && total < 16
      end

      def self.encode_levels(writer, levels, trailing)
        levels.each_with_index do |level, index|
          suffix_size = [0, index - trailing + 1].max
          abs = level.abs
          prefix = [abs * 2 - (level.negative? ? 1 : 2), 0].max
          writer.write_ue(prefix)
          writer.write_bits(abs, suffix_size) if suffix_size.positive?
        end
      end

      def self.encode_total_zeros(writer, total, zeros)
        table = TOTAL_ZEROS[total] || TOTAL_ZEROS[1]
        write_codeword(writer, table[zeros.clamp(0, 1)] || table.values.last)
      end

      def self.lookup_coeff_token(nc, total, trailing)
        table = COEFF_TOKEN[nc.clamp(0, 2)] || COEFF_TOKEN[0]
        entry = table[total] || table[1]
        entry[trailing] || entry.values.last
      end

      def self.write_codeword(writer, codeword)
        if codeword.is_a?(Integer)
          writer.write_bits(codeword, 1)
        else
          codeword.each { |bit| writer.write_bits(bit, 1) }
        end
      end

      def self.hadamard4x4(values)
        padded = values.take(16)
        padded += [0] * (16 - padded.length)
        matrix = padded.each_slice(4).map(&:dup)
        4.times do |row|
          a, b, c, d = matrix[row]
          matrix[row] = [a + d, b + c, b - c, a - d]
        end
        4.times do |col|
          a = matrix[0][col]
          b = matrix[1][col]
          c = matrix[2][col]
          d = matrix[3][col]
          matrix[0][col] = a + d
          matrix[1][col] = b + c
          matrix[2][col] = b - c
          matrix[3][col] = a - d
        end
        matrix.flatten
      end
    end
  end
end
