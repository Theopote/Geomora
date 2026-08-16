# frozen_string_literal: true

module Geomora
  module Core
    class ViewportStream
      DEFAULT_INTERVAL = 1.0

      @timer_id = nil
      @dialog = nil

      class << self
        attr_accessor :timer_id, :dialog
      end

      def self.start(dialog, interval: DEFAULT_INTERVAL)
        stop
        self.dialog = dialog
        return start_js_fallback(interval) unless sketchup_timer?

        self.timer_id = ::UI.start_timer(interval.to_f, true) do
          push_snapshot(dialog)
        end
        Logger.info("Viewport stream started (#{interval}s)")
        true
      end

      def self.stop
        if timer_id && sketchup_timer?
          ::UI.stop_timer(timer_id)
        end
        self.timer_id = nil
        self.dialog = nil
        Logger.info('Viewport stream stopped')
      end

      def self.active?
        !timer_id.nil?
      end

      def self.push_snapshot(dialog)
        snapshot = ViewportSnapshot.capture
        dialog.execute_script("window.geomora.setViewportSnapshot(#{snapshot.to_json})")
      rescue GeomoraError => e
        Logger.warn("Viewport stream capture failed: #{e.message}")
      end

      def self.sketchup_timer?
        defined?(::UI) && ::UI.respond_to?(:start_timer) && ::UI.respond_to?(:stop_timer)
      end

      def self.start_js_fallback(interval)
        dialog.execute_script("window.geomora.startViewportStreamFallback(#{interval.to_f})")
        true
      end
    end
  end
end
