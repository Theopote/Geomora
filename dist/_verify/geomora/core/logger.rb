# frozen_string_literal: true

module Geomora
  module Logger
    LEVELS = {
      debug: 0,
      info: 1,
      warn: 2,
      error: 3
    }.freeze

    @level = :info

    class << self
      attr_accessor :level

      LEVELS.each_key do |name|
        define_method(name) do |message|
          log(name, message)
        end
      end

      private

      def log(level, message)
        return if LEVELS[level] < LEVELS[@level]

        prefix = "[Geomora][#{level.to_s.upcase}]"
        puts "#{prefix} #{message}"
      end
    end
  end
end
