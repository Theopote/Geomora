# frozen_string_literal: true

require 'json'

module Geomora
  module Core
    class LodPresentation
      def self.geomora_pages(model)
        return [] unless model.respond_to?(:pages)

        names = LodScenePages.page_names
        LodScenes::PRESETS.values.map do |level|
          LodScenePages.find_page(model, LodScenePages.page_name_for(level))
        end.compact
      end

      def self.next_scene(model)
        pages = geomora_pages(model)
        raise GeomoraError, 'No Geomora LOD scenes found. Create LOD Scene Pages first.' if pages.empty?

        current = model.pages.selected_page
        current_index = pages.index(current)
        next_index = current_index.nil? ? 0 : (current_index + 1) % pages.length
        page = pages[next_index]
        model.pages.selected_page = page
        level = level_from_page_name(page.name)
        LodVisibility.apply(model, level) if level
        page.name
      end

      def self.tour_manifest(model)
        geomora_pages(model).map.with_index do |page, index|
          {
            'order' => index + 1,
            'name' => page.name,
            'lod_level' => level_from_page_name(page.name)
          }
        end
      end

      def self.export_tour_json(model)
        tour_manifest(model).to_json
      end

      def self.export_tour_file(model, path)
        manifest = tour_manifest(model)
        raise GeomoraError, 'No Geomora LOD scenes found. Create LOD Scene Pages first.' if manifest.empty?

        File.write(path, JSON.pretty_generate(manifest))
        path
      end

      def self.export_tour_html(model, path, step_seconds: 2.0)
        manifest = tour_manifest(model)
        raise GeomoraError, 'No Geomora LOD scenes found. Create LOD Scene Pages first.' if manifest.empty?

        interval_ms = (step_seconds.to_f * 1000).round
        slides = manifest.map.with_index do |entry, index|
          level = entry['lod_level']
          active = index.zero? ? ' active' : ''
          <<~SLIDE.strip
            <section class="slide#{active}" data-level="#{level}">
              <div class="badge">Step #{entry['order']}</div>
              <h1>#{escape_html(entry['name'])}</h1>
              <p class="lod">LOD #{level}</p>
              <p class="hint">Open this model in SketchUp at the matching LOD scene for a live view.</p>
            </section>
          SLIDE
        end.join("\n")

        html = <<~HTML
          <!DOCTYPE html>
          <html lang="en">
          <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Geomora LOD Tour</title>
            <style>
              :root { color-scheme: dark; font-family: "Segoe UI", system-ui, sans-serif; }
              body { margin: 0; background: #111; color: #f5f5f5; }
              .deck { min-height: 100vh; display: grid; place-items: center; padding: 2rem; }
              .slide { display: none; text-align: center; max-width: 42rem; animation: fade 0.6s ease; }
              .slide.active { display: block; }
              .badge { display: inline-block; margin-bottom: 1rem; padding: 0.35rem 0.75rem; border-radius: 999px; background: #2d6cdf; font-size: 0.85rem; }
              h1 { margin: 0 0 0.5rem; font-size: 2rem; }
              .lod { font-size: 3rem; font-weight: 700; margin: 0.5rem 0 1rem; color: #8ec5ff; }
              .hint { color: #aaa; line-height: 1.5; }
              .progress { position: fixed; left: 0; right: 0; bottom: 0; height: 4px; background: #333; }
              .progress > span { display: block; height: 100%; width: 0; background: #2d6cdf; transition: width 0.3s ease; }
              @keyframes fade { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
            </style>
          </head>
          <body>
            <main class="deck">
              #{slides}
            </main>
            <div class="progress"><span id="progress"></span></div>
            <script>
              const slides = Array.from(document.querySelectorAll('.slide'));
              const progress = document.getElementById('progress');
              let index = 0;
              function showSlide(nextIndex) {
                slides[index].classList.remove('active');
                index = nextIndex % slides.length;
                slides[index].classList.add('active');
                progress.style.width = ((index + 1) / slides.length * 100) + '%';
              }
              setInterval(function () { showSlide(index + 1); }, #{interval_ms});
              progress.style.width = (100 / slides.length) + '%';
            </script>
          </body>
          </html>
        HTML

        File.write(path, html)
        path
      end

      def self.export_tour_capture_html(model, path, step_seconds: 2.0, width: LodCapture::DEFAULT_WIDTH, height: LodCapture::DEFAULT_HEIGHT)
        frames = LodCapture.capture_pages(model, width: width, height: height)
        raise GeomoraError, 'No Geomora LOD scenes found. Create LOD Scene Pages first.' if frames.empty?

        interval_ms = (step_seconds.to_f * 1000).round
        slides = frames.map.with_index do |frame, index|
          active = index.zero? ? ' active' : ''
          src = "data:image/png;base64,#{frame['base64']}"
          <<~SLIDE.strip
            <section class="slide#{active}" data-level="#{frame['lod_level']}">
              <div class="badge">Step #{frame['order']}</div>
              <h1>#{escape_html(frame['name'])}</h1>
              <img src="#{src}" alt="#{escape_html(frame['name'])}" width="#{width}" height="#{height}">
              <p class="lod">LOD #{frame['lod_level']}</p>
            </section>
          SLIDE
        end.join("\n")

        html = <<~HTML
          <!DOCTYPE html>
          <html lang="en">
          <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Geomora LOD Capture Tour</title>
            <style>
              :root { color-scheme: dark; font-family: "Segoe UI", system-ui, sans-serif; }
              body { margin: 0; background: #111; color: #f5f5f5; }
              .deck { min-height: 100vh; display: grid; place-items: center; padding: 2rem; }
              .slide { display: none; text-align: center; max-width: 100%; animation: fade 0.6s ease; }
              .slide.active { display: block; }
              .slide img { max-width: min(960px, 100%); height: auto; border-radius: 8px; box-shadow: 0 12px 40px rgba(0,0,0,0.45); }
              .badge { display: inline-block; margin-bottom: 1rem; padding: 0.35rem 0.75rem; border-radius: 999px; background: #2d6cdf; font-size: 0.85rem; }
              h1 { margin: 0 0 0.5rem; font-size: 1.5rem; }
              .lod { font-size: 1.25rem; color: #8ec5ff; }
              .progress { position: fixed; left: 0; right: 0; bottom: 0; height: 4px; background: #333; }
              .progress > span { display: block; height: 100%; width: 0; background: #2d6cdf; transition: width 0.3s ease; }
              @keyframes fade { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
            </style>
          </head>
          <body>
            <main class="deck">#{slides}</main>
            <div class="progress"><span id="progress"></span></div>
            <script>
              const slides = Array.from(document.querySelectorAll('.slide'));
              const progress = document.getElementById('progress');
              let index = 0;
              function showSlide(nextIndex) {
                slides[index].classList.remove('active');
                index = nextIndex % slides.length;
                slides[index].classList.add('active');
                progress.style.width = ((index + 1) / slides.length * 100) + '%';
              }
              setInterval(function () { showSlide(index + 1); }, #{interval_ms});
              progress.style.width = (100 / slides.length) + '%';
            </script>
          </body>
          </html>
        HTML

        File.write(path, html)
        path
      end

      def self.export_tour_frames(model, directory, width: LodCapture::DEFAULT_WIDTH, height: LodCapture::DEFAULT_HEIGHT)
        LodCapture.export_frames(model, directory, width: width, height: height)
      end

      def self.export_tour_gif(model, path, delay_centiseconds: 20, width: LodCapture::DEFAULT_WIDTH, height: LodCapture::DEFAULT_HEIGHT)
        LodCapture.export_gif(model, path, delay_centiseconds: delay_centiseconds, width: width, height: height)
      end

      def self.export_tour_video(model, path, format: 'mp4', fps: LodVideoExporter::DEFAULT_FPS)
        LodVideoExporter.export(model, path, format: format, fps: fps)
      end

      def self.export_tour_avi(model, path, fps: LodVideoExporter::DEFAULT_FPS)
        LodCapture.export_avi(model, path, fps: fps)
      end

      def self.export_tour_mp4_native(model, path, fps: LodVideoExporter::DEFAULT_FPS)
        LodVideoExporter.export_native_mp4(model, path, fps: fps)
      end

      def self.export_tour_h264_mp4(model, path, fps: LodVideoExporter::DEFAULT_FPS)
        LodVideoExporter.export_h264_mp4(model, path, fps: fps)
      end

      def self.escape_html(text)
        text.to_s
            .gsub('&', '&amp;')
            .gsub('<', '&lt;')
            .gsub('>', '&gt;')
            .gsub('"', '&quot;')
      end

      def self.play_tour(model, step_seconds: 2.0)
        pages = geomora_pages(model)
        raise GeomoraError, 'No Geomora LOD scenes found. Create LOD Scene Pages first.' if pages.empty?

        unless defined?(::UI) && ::UI.respond_to?(:start_timer)
          pages.each_with_index do |page, index|
            activate_page(model, page)
            Logger.info("LOD tour step #{index + 1}: #{page.name}")
          end
          return pages.map(&:name)
        end

        pages.each_with_index do |page, index|
          delay = step_seconds * index
          ::UI.start_timer(delay, false) do
            activate_page(model, page)
          end
        end
        pages.map(&:name)
      end

      def self.activate_page(model, page)
        model.pages.selected_page = page
        level = level_from_page_name(page.name)
        LodVisibility.apply(model, level) if level
      end

      def self.level_from_page_name(name)
        match = name.to_s.match(/LOD\s+(\d+)/)
        return nil unless match

        match[1].to_i
      end
    end
  end
end
