# frozen_string_literal: true

module Geomora
  module Transactions
    class Operation
      def self.run(name, model)
        model.start_operation(name, true)
        begin
          result = yield
          model.commit_operation
          result
        rescue StandardError
          model.abort_operation
          raise
        end
      end
    end
  end
end
