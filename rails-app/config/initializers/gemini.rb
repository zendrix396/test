#easy
begin
  require 'gemini-ai'

  if defined?(Gemini) && Gemini.respond_to?(:configure)
    Gemini.configure do |config|
      # Prefer ENV for easier Windows setup; fallback to Rails credentials
      config.api_key = ENV['GOOGLE_API_KEY'] || Rails.application.credentials.dig(:google, :api_key)
    end
  else
    # The gem version in use doesn't expose Gemini.configure; ensure ENV is set for HTTP usage
    ENV['GOOGLE_API_KEY'] ||= Rails.application.credentials.dig(:google, :api_key).to_s if defined?(Rails)
  end
rescue LoadError => e
  Rails.logger.warn("Gemini AI not loaded: #{e.message}") if defined?(Rails)
end

