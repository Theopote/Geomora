# frozen_string_literal: true

module Geomora
  module Core
    class H264FrameEncoder
      PROFILE_BASELINE = 66
      LEVEL_3 = 30

      def self.configuration(width, height)
        width = align16(width)
        height = align16(height)
        {
          'width' => width,
          'height' => height,
          'sps' => "\x67".b + build_sps(width, height),
          'pps' => "\x68".b + build_pps
        }
      end

      def self.encode_idr(rgb, src_width, src_height, config)
        width = config['width']
        height = config['height']
        padded = pad_rgb(rgb, src_width, src_height, width, height)
        yuv = rgb_to_yuv420(padded, width, height)
        slice = build_idr_slice(yuv, width, height)
        H264Bitstream.nal_unit(5, slice)
      end

      def self.pad_rgb(rgb, src_width, src_height, dst_width, dst_height)
        out = String.new(encoding: Encoding::ASCII_8BIT)
        dst_height.times do |y|
          dst_width.times do |x|
            if x < src_width && y < src_height
              base = (y * src_width + x) * 3
              out << rgb[base, 3]
            else
              out << "\x10\x10\x10"
            end
          end
        end
        out
      end

      def self.align16(value)
        ((value.to_i + 15) / 16) * 16
      end

      def self.rgb_to_yuv420(rgb, width, height)
        y = Array.new(width * height, 16)
        u = Array.new((width / 2) * (height / 2), 128)
        v = Array.new((width / 2) * (height / 2), 128)

        height.times do |y_pos|
          width.times do |x_pos|
            base = (y_pos * width + x_pos) * 3
            r = rgb.getbyte(base)
            g = rgb.getbyte(base + 1)
            b = rgb.getbyte(base + 2)
            y_val = ((0.299 * r) + (0.587 * g) + (0.114 * b)).round.clamp(0, 255)
            y[y_pos * width + x_pos] = y_val
            next unless x_pos.even? && y_pos.even?

            u_idx = (y_pos / 2) * (width / 2) + (x_pos / 2)
            u[u_idx] = ((-0.169 * r) - (0.331 * g) + (0.500 * b) + 128).round.clamp(0, 255)
            v[u_idx] = ((0.500 * r) - (0.419 * g) - (0.081 * b) + 128).round.clamp(0, 255)
          end
        end
        { 'y' => y, 'u' => u, 'v' => v }
      end

      def self.build_sps(width, height)
        writer = H264Bitstream::Writer.new
        writer.write_bits(PROFILE_BASELINE, 8)
        writer.write_bits(0, 8) # constraint_set flags + reserved
        writer.write_bits(LEVEL_3, 8)
        writer.write_ue(0) # seq_parameter_set_id
        writer.write_ue(4) # log2_max_frame_num_minus4 -> 8 bits
        writer.write_ue(2) # pic_order_cnt_type
        writer.write_ue(1) # max_num_ref_frames
        writer.write_ue(0) # gaps_in_frame_num_value_allowed_flag
        mbs_w = (width / 16) - 1
        mbs_h = (height / 16) - 1
        writer.write_ue(mbs_w)
        writer.write_ue(mbs_h)
        writer.write_bits(1, 1) # frame_mbs_only_flag
        writer.write_bits(1, 1) # direct_8x8_inference_flag
        writer.write_bits(0, 1) # frame_cropping_flag
        writer.write_bits(0, 1) # vui_parameters_present_flag
        writer.align_byte
        writer.bytes
      end

      def self.build_pps
        writer = H264Bitstream::Writer.new
        writer.write_ue(0) # pic_parameter_set_id
        writer.write_ue(0) # seq_parameter_set_id
        writer.write_bits(1, 1) # entropy_coding_mode_flag = CAVLC
        writer.write_bits(0, 1) # bottom_field_pic_order_in_frame_present_flag
        writer.write_ue(0) # num_slice_groups_minus1
        writer.write_ue(0) # num_ref_idx_l0_default_active_minus1
        writer.write_ue(0) # num_ref_idx_l1_default_active_minus1
        writer.write_bits(0, 1) # weighted_pred_flag
        writer.write_bits(0, 2) # weighted_bipred_idc
        writer.write_se(0) # pic_init_qp_minus26 -> qp 26
        writer.write_se(0) # pic_init_qs_minus26
        writer.write_se(0) # chroma_qp_index_offset
        writer.write_bits(1, 1) # deblocking_filter_control_present_flag
        writer.write_bits(0, 1) # constrained_intra_pred_flag
        writer.write_bits(0, 1) # redundant_pic_cnt_present_flag
        writer.align_byte
        writer.bytes
      end

      def self.build_idr_slice(yuv, width, height)
        writer = H264Bitstream::Writer.new
        writer.write_ue(0) # first_mb_in_slice
        writer.write_ue(2) # slice_type I
        writer.write_ue(0) # pic_parameter_set_id
        writer.write_bits(0, 4) # frame_num
        writer.write_ue(0) # idr_pic_id
        mb_cols = width / 16
        mb_rows = height / 16
        mb_rows.times do |mb_y|
          mb_cols.times do |mb_x|
            write_intra16x16_macroblock(writer, yuv, width, mb_x, mb_y)
          end
        end
        writer.write_bits(1, 1) # rbsp_stop_one_bit
        writer.align_byte
        writer.bytes
      end

      def self.write_intra16x16_macroblock(writer, yuv, width, mb_x, mb_y)
        writer.write_ue(0) # I_16x16_0_0_0
        luma_dcs = extract_luma_dcs(yuv, width, mb_x, mb_y)
        cb_dcs = extract_chroma_dcs(yuv, width, mb_x, mb_y, 'u')
        cr_dcs = extract_chroma_dcs(yuv, width, mb_x, mb_y, 'v')
        H264Cavlc.encode_intra16x16_residual(writer, luma_dcs, cb_dcs, cr_dcs)
      end

      def self.extract_luma_dcs(yuv, width, mb_x, mb_y)
        16.times.map do |block|
          block_x = (mb_x * 16) + ((block % 4) * 4)
          block_y = (mb_y * 16) + ((block / 4) * 4)
          sum = 0
          16.times do |index|
            x = block_x + (index % 4)
            y = block_y + (index / 4)
            sum += yuv['y'][(y * width) + x]
          end
          sum / 16
        end
      end

      def self.extract_chroma_dcs(yuv, width, mb_x, mb_y, plane)
        plane_data = yuv[plane]
        chroma_width = width / 2
        4.times.map do |block|
          block_x = (mb_x * 8) + ((block % 2) * 4)
          block_y = (mb_y * 8) + ((block / 2) * 4)
          sum = 0
          16.times do |index|
            x = block_x + (index % 4)
            y = block_y + (index / 4)
            sum += plane_data[(y * chroma_width) + x]
          end
          sum / 16
        end
      end

      # Legacy I_PCM path kept for debugging/comparison.
      def self.write_ipcm_macroblock(writer, yuv, width, mb_x, mb_y)
        writer.write_ue(25) # I_PCM
        writer.write_bits(0, 1) # pcm_alignment_zero_bit
        16.times do |row|
          16.times do |col|
            x = (mb_x * 16) + col
            y = (mb_y * 16) + row
            writer.write_bits(yuv['y'][(y * width) + x], 8)
          end
        end
        8.times do |row|
          8.times do |col|
            idx = ((mb_y * 8) + row) * (width / 2) + (mb_x * 8) + col
            writer.write_bits(yuv['u'][idx], 8)
          end
        end
        8.times do |row|
          8.times do |col|
            idx = ((mb_y * 8) + row) * (width / 2) + (mb_x * 8) + col
            writer.write_bits(yuv['v'][idx], 8)
          end
        end
      end
    end
  end
end
