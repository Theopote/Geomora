# frozen_string_literal: true

module Geomora
  module Core
    class PdfReportExporter
      PAGE_WIDTH = 595
      PAGE_HEIGHT = 842
      MARGIN = 36

      def self.export(params, path)
        storeys = RoomLayoutEditor.preview_all_storeys(params)
        raise GeomoraError, 'No rooms to export' if storeys.empty?

        pages = storeys.flat_map do |storey|
          (storey['rooms'] || []).map do |room|
            render_page(storey, room)
          end
        end
        write_pdf(path, pages)
        path
      end

      def self.export_booklet(params, path)
        storeys = RoomLayoutEditor.preview_all_storeys(params)
        raise GeomoraError, 'No rooms to export' if storeys.empty?

        room_pages = storeys.flat_map do |storey|
          (storey['rooms'] || []).map do |room|
            { 'storey' => storey, 'room' => room }
          end
        end
        pages = [render_cover_page(room_pages.length), render_toc_page(room_pages)]
        room_pages.each_slice(2) do |pair|
          pages << render_spread_page(pair)
        end
        write_pdf(path, pages)
        path
      end

      def self.render_cover_page(room_count)
        lines = [
          title_commands('Geomora Layout Booklet'),
          "BT /F1 12 Tf #{MARGIN} #{PAGE_HEIGHT - MARGIN - 40} Td (#{escape_pdf('Room layout reference')}) Tj ET",
          "BT /F1 10 Tf #{MARGIN} #{PAGE_HEIGHT - MARGIN - 64} Td (#{escape_pdf(Time.now.utc.strftime('%Y-%m-%d %H:%M UTC'))}) Tj ET",
          "BT /F1 10 Tf #{MARGIN} #{PAGE_HEIGHT - MARGIN - 80} Td (#{escape_pdf("#{room_count} rooms")}) Tj ET"
        ]
        lines.join("\n")
      end

      def self.render_toc_page(room_pages)
        lines = [title_commands('Contents')]
        room_pages.each_with_index do |entry, index|
          label = "#{entry['storey']['label']} — #{entry['room']['name']}"
          y = PAGE_HEIGHT - MARGIN - 48 - (index * 16)
          lines << "BT /F1 10 Tf #{MARGIN} #{y} Td (#{escape_pdf("#{index + 1}. #{label}")}) Tj ET"
        end
        lines.join("\n")
      end

      def self.render_spread_page(pair)
        pair.map.with_index do |entry, column|
          render_page_column(entry['storey'], entry['room'], column)
        end.join("\n")
      end

      def self.render_page_column(storey, room, column)
        bounds = LayoutReportExporter.send(:symbolize_bounds, room['bounds'])
        scale = scale_for(bounds) * 0.85
        column_width = (PAGE_WIDTH - (MARGIN * 3)) / 2
        origin_x = MARGIN + (column * (column_width + MARGIN))
        origin_y = PAGE_HEIGHT - MARGIN - 80
        commands = []
        commands << "BT /F1 11 Tf #{origin_x} #{PAGE_HEIGHT - MARGIN - 24} Td (#{escape_pdf("#{storey['label']} — #{room['name']}")}) Tj ET"
        commands << room_commands(bounds, origin_x, origin_y, scale)
        (room['items'] || []).each do |item|
          commands << item_commands(item, bounds, origin_x, origin_y, scale)
        end
        commands.join("\n")
      end

      def self.render_page(storey, room)
        bounds = LayoutReportExporter.send(:symbolize_bounds, room['bounds'])
        scale = scale_for(bounds)
        origin_x = MARGIN
        origin_y = PAGE_HEIGHT - MARGIN - 120
        commands = []
        commands << title_commands("#{storey['label']} — #{room['name']}")
        commands << room_commands(bounds, origin_x, origin_y, scale)
        (room['items'] || []).each do |item|
          commands << item_commands(item, bounds, origin_x, origin_y, scale)
        end
        commands << table_commands(room['items'] || [], origin_y - ((bounds[:y_max] - bounds[:y_min]) * scale) - 24)
        commands.join("\n")
      end

      def self.scale_for(bounds)
        width = bounds[:x_max] - bounds[:x_min]
        height = bounds[:y_max] - bounds[:y_min]
        max_w = PAGE_WIDTH - (MARGIN * 2)
        max_h = 360
        [max_w / width, max_h / height].min
      end

      def self.title_commands(title)
        "BT /F1 14 Tf #{MARGIN} #{PAGE_HEIGHT - MARGIN} Td (#{escape_pdf(title)}) Tj ET"
      end

      def self.room_commands(bounds, origin_x, origin_y, scale)
        w = (bounds[:x_max] - bounds[:x_min]) * scale
        h = (bounds[:y_max] - bounds[:y_min]) * scale
        [
          '0.9 0.92 0.96 rg',
          "#{origin_x} #{origin_y - h} #{w} #{h} re f",
          '0.45 0.5 0.6 RG 1 w',
          "#{origin_x} #{origin_y - h} #{w} #{h} re S"
        ].join("\n")
      end

      def self.item_commands(item, bounds, origin_x, origin_y, scale)
        pos = item['position'] || [0, 0, 0]
        x = origin_x + ((pos[0] - bounds[:x_min]) * scale)
        y = origin_y - ((pos[1] - bounds[:y_min]) * scale) - (item['depth'] * scale)
        w = item['width'] * scale
        h = item['depth'] * scale
        [
          '0.55 0.72 0.95 rg',
          "#{x} #{y} #{w} #{h} re f",
          '0.1 0.1 0.1 RG',
          "#{x} #{y} #{w} #{h} re S",
          "BT /F1 8 Tf #{x + 2} #{y + 10} Td (#{escape_pdf(item['kind'])}) Tj ET"
        ].join("\n")
      end

      def self.table_commands(items, start_y)
        lines = ["BT /F1 10 Tf #{MARGIN} #{start_y} Td (Item list:) Tj ET"]
        items.each_with_index do |item, index|
          pos = item['position'] || [0, 0, 0]
          text = format(
            '%s @ %d,%d (%dx%dx%d mm)',
            item['kind'], pos[0].round, pos[1].round,
            item['width'].round, item['depth'].round, item['height'].round
          )
          y = start_y - 16 - (index * 12)
          lines << "BT /F1 9 Tf #{MARGIN} #{y} Td (#{escape_pdf(text)}) Tj ET"
        end
        lines.join("\n")
      end

      def self.write_pdf(path, pages)
        objects = []
        objects << pdf_object(1, '<< /Type /Catalog /Pages 2 0 R >>')
        kids = pages.each_with_index.map { |_, index| "#{index + 3} 0 R" }.join(' ')
        objects << pdf_object(2, "<< /Type /Pages /Kids [#{kids}] /Count #{pages.length} >>")
        font_obj = pages.length + 3
        objects << pdf_object(font_obj, '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
        pages.each_with_index do |content, index|
          page_id = index + 3
          content_id = page_id + pages.length + 1
          stream = wrap_stream(content)
          objects << pdf_object(
            page_id,
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 #{PAGE_WIDTH} #{PAGE_HEIGHT}] " \
            "/Contents #{content_id} 0 R /Resources << /Font << /F1 #{font_obj} 0 R >> >> >>"
          )
          objects << pdf_object(content_id, stream, stream: true)
        end
        File.write(path, build_file(objects))
      end

      def self.wrap_stream(content)
        "<< /Length #{content.bytesize} >>\nstream\n#{content}\nendstream"
      end

      def self.pdf_object(id, body, stream: false)
        { id: id, body: body, stream: stream }
      end

      def self.build_file(objects)
        output = +"%PDF-1.4\n"
        offsets = [0]
        objects.each do |object|
          offsets << output.bytesize
          output << "#{object[:id]} 0 obj\n#{object[:body]}\nendobj\n"
        end
        xref = output.bytesize
        output << "xref\n0 #{objects.length + 1}\n"
        output << "0000000000 65535 f \n"
        offsets[1..].each do |offset|
          output << format("%010d 00000 n \n", offset)
        end
        output << "trailer\n<< /Size #{objects.length + 1} /Root 1 0 R >>\n"
        output << "startxref\n#{xref}\n%%EOF\n"
        output
      end

      def self.escape_pdf(text)
        text.to_s.gsub('\\', '\\\\').gsub('(', '\\(').gsub(')', '\\)')
      end
    end
  end
end
