# frozen_string_literal: true

require 'sketchup.rb'

module Geomora
  module Boot
    LOAD_MARKER = 'geomora_ui_registered'

    def self.start
      require File.join(__dir__, 'loader')

      register_ui_with_retry
      Logger.info("Geomora #{VERSION} boot complete")
    rescue StandardError => e
      report_error(e)
      raise
    end

    def self.register_ui_with_retry
      return if file_loaded?(LOAD_MARKER)

      register_ui
      file_loaded(LOAD_MARKER)
    rescue StandardError => e
      Logger.warn("Immediate UI registration failed, retrying: #{e.message}")
      ::UI.start_timer(0.5, false) do
        register_ui unless file_loaded?(LOAD_MARKER)
        file_loaded(LOAD_MARKER)
        Logger.info('Geomora UI registered (deferred)')
      rescue StandardError => retry_error
        report_error(retry_error)
      end
    end

    def self.register_ui
      AppUI::Commands.register
    end

    def self.report_error(error)
      message = [
        'Geomora failed to load.',
        '',
        error.message,
        '',
        error.backtrace&.first(10)&.join("\n")
      ].join("\n")

      Logger.error(error.message)
      begin
        ::UI.messagebox(message)
      rescue StandardError
        puts message
      end
    end
  end

  Boot.start
end
