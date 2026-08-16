# frozen_string_literal: true

require 'zlib'

module Geomora
  module Core
    class PngReader
      SIGNATURE = [137, 80, 78, 71, 13, 10, 26, 10].pack('C*')

      def self.read_rgb(path)
        data = File.binread(path)
        raise GeomoraError, "Not a PNG file: #{path}" unless data.start_with?(SIGNATURE)

        width = nil
        height = nil
        bit_depth = nil
        color_type = nil
        idat = +''
        pos = 8
        while pos < data.bytesize
          length = data[pos, 4].unpack1('N')
          type = data[pos + 4, 4]
          chunk = data[pos + 8, length]
          pos += 12 + length
          case type
          when 'IHDR'
            width, height, bit_depth, color_type = chunk.unpack('NNCC')
          when 'IDAT'
            idat << chunk
          when 'IEND'
            break
          end
        end
        raise GeomoraError, 'Unsupported PNG format' unless width && height && bit_depth == 8 && [2, 6].include?(color_type)

        inflated = Zlib::Inflate.inflate(idat)
        bytes_per_pixel = color_type == 6 ? 4 : 3
        stride = (width * bytes_per_pixel) + 1
        rgb = +''
        previous = "\0" * (width * bytes_per_pixel)
        height.times do |row|
          offset = row * stride
          filter = inflated.getbyte(offset)
          scanline = inflated.byteslice(offset + 1, width * bytes_per_pixel).dup
          scanline = unfilter(filter, scanline, previous, bytes_per_pixel)
          width.times do |col|
            base = col * bytes_per_pixel
            rgb << scanline.getbyte(base).chr << scanline.getbyte(base + 1).chr << scanline.getbyte(base + 2).chr
          end
          previous = scanline
        end
        { 'width' => width, 'height' => height, 'rgb' => rgb }
      end

      def self.unfilter(filter_type, scanline, previous, bpp)
        case filter_type
        when 0
          scanline
        when 1
          recon_sub(scanline, bpp)
        when 2
          recon_up(scanline, previous)
        when 3
          recon_average(scanline, previous, bpp)
        when 4
          recon_paeth(scanline, previous, bpp)
        else
          scanline
        end
      end

      def self.recon_sub(scanline, bpp)
        out = scanline.dup
        (bpp...out.bytesize).each do |index|
          out.setbyte(index, (out.getbyte(index) + out.getbyte(index - bpp)) % 256)
        end
        out
      end

      def self.recon_up(scanline, previous)
        out = scanline.dup
        out.bytesize.times do |index|
          out.setbyte(index, (out.getbyte(index) + previous.getbyte(index)) % 256)
        end
        out
      end

      def self.recon_average(scanline, previous, bpp)
        out = scanline.dup
        out.bytesize.times do |index|
          left = index >= bpp ? out.getbyte(index - bpp) : 0
          up = previous.getbyte(index)
          out.setbyte(index, (out.getbyte(index) + ((left + up) / 2)) % 256)
        end
        out
      end

      def self.recon_paeth(scanline, previous, bpp)
        out = scanline.dup
        out.bytesize.times do |index|
          left = index >= bpp ? out.getbyte(index - bpp) : 0
          up = previous.getbyte(index)
          up_left = index >= bpp ? previous.getbyte(index - bpp) : 0
          out.setbyte(index, (out.getbyte(index) + paeth_predictor(left, up, up_left)) % 256)
        end
        out
      end

      def self.paeth_predictor(left, up, up_left)
        p = left + up - up_left
        pa = (p - left).abs
        pb = (p - up).abs
        pc = (p - up_left).abs
        return left if pa <= pb && pa <= pc
        return up if pb <= pc

        up_left
      end
    end
  end
end
