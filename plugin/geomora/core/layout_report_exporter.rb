# frozen_string_literal: true

module Geomora
  module Core
    class LayoutReportExporter
      SCALE = 0.08

      def self.export_html(params, path)
        storeys = RoomLayoutEditor.preview_all_storeys(params)
        raise GeomoraError, 'No rooms to export' if storeys.empty?

        pages = storeys.flat_map do |storey|
          (storey['rooms'] || []).map do |room|
            render_room_page(storey, room)
          end
        end

        html = <<~HTML
          <!DOCTYPE html>
          <html lang="en">
          <head>
            <meta charset="utf-8">
            <title>Geomora Layout Report</title>
            <style>
              body { font-family: "Segoe UI", sans-serif; margin: 24px; color: #111; }
              h1 { margin-bottom: 4px; }
              .meta { color: #555; margin-bottom: 24px; }
              .page { page-break-after: always; margin-bottom: 48px; }
              .page:last-child { page-break-after: auto; }
              svg { border: 1px solid #ccc; background: #f8f9fa; }
              table { border-collapse: collapse; margin-top: 12px; width: 100%; max-width: 640px; }
              th, td { border: 1px solid #ddd; padding: 6px 8px; text-align: left; font-size: 13px; }
              th { background: #eef2f7; }
              @media print { body { margin: 12mm; } .page { page-break-after: always; } }
            </style>
          </head>
          <body>
            <h1>Geomora Layout Report</h1>
            <div class="meta">Generated #{Time.now.utc.strftime('%Y-%m-%d %H:%M UTC')} · #{pages.length} rooms</div>
            #{pages.join("\n")}
          </body>
          </html>
        HTML

        File.write(path, html)
        path
      end

      def self.export_pdf(params, path)
        PdfReportExporter.export(params, path)
      end

      def self.export_pdf_booklet(params, path)
        PdfReportExporter.export_booklet(params, path)
      end

      def self.render_room_page(storey, room)
        bounds = symbolize_bounds(room['bounds'])
        svg = render_svg(bounds, room['items'] || [])
        rows = (room['items'] || []).map do |item|
          pos = item['position'] || [0, 0, 0]
          "<tr><td>#{escape(item['kind'])}</td><td>#{pos[0].round}, #{pos[1].round}</td>" \
            "<td>#{item['width'].round}×#{item['depth'].round}×#{item['height'].round}</td></tr>"
        end.join

        <<~HTML
          <section class="page">
            <h2>#{escape(storey['label'])} — #{escape(room['name'])}</h2>
            #{svg}
            <table>
              <thead><tr><th>Item</th><th>Position (mm)</th><th>W×D×H (mm)</th></tr></thead>
              <tbody>#{rows}</tbody>
            </table>
          </section>
        HTML
      end

      def self.render_svg(bounds, items)
        width = ((bounds[:x_max] - bounds[:x_min]) * SCALE).round + 40
        height = ((bounds[:y_max] - bounds[:y_min]) * SCALE).round + 40
        room_rect = svg_rect(
          20,
          20,
          (bounds[:x_max] - bounds[:x_min]) * SCALE,
          (bounds[:y_max] - bounds[:y_min]) * SCALE,
          fill: '#e8edf5',
          stroke: '#5f6b7c'
        )
        furniture = items.map do |item|
          pos = item['position'] || [0, 0, 0]
          x = 20 + ((pos[0] - bounds[:x_min]) * SCALE)
          y = 20 + ((pos[1] - bounds[:y_min]) * SCALE)
          svg_rect(x, y, item['width'] * SCALE, item['depth'] * SCALE, fill: '#8ab4f8', stroke: '#1a1a1a') +
            %(<text x="#{x + 4}" y="#{y + 12}" font-size="10">#{escape(item['kind'])}</text>)
        end.join
        %(<svg width="#{width}" height="#{height}" xmlns="http://www.w3.org/2000/svg">#{room_rect}#{furniture}</svg>)
      end

      def self.svg_rect(x, y, w, h, fill:, stroke:)
        %(<rect x="#{x.round(2)}" y="#{y.round(2)}" width="#{w.round(2)}" height="#{h.round(2)}" fill="#{fill}" stroke="#{stroke}"/>)
      end

      def self.symbolize_bounds(bounds)
        {
          x_min: bounds['x_min'].to_f,
          x_max: bounds['x_max'].to_f,
          y_min: bounds['y_min'].to_f,
          y_max: bounds['y_max'].to_f
        }
      end

      def self.escape(text)
        text.to_s.gsub('&', '&amp;').gsub('<', '&lt;').gsub('>', '&gt;')
      end
    end
  end
end
