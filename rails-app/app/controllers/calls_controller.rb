class CallsController < ApplicationController
  def index
    @calls = Call.order(created_at: :desc)
  end

  def new
  end

  def create
    phone_numbers = params[:phone_numbers].to_s.split(/[\n,]/).map(&:strip).reject(&:blank?)
    
    if phone_numbers.empty?
      redirect_to new_call_path, alert: "Please enter at least one phone number."
      return
    end

    account_sid = ENV['TWILIO_ACCOUNT_SID'] || Rails.application.credentials.dig(:twilio, :account_sid)
    auth_token = ENV['TWILIO_AUTH_TOKEN'] || Rails.application.credentials.dig(:twilio, :auth_token)
    from_number = ENV['TWILIO_FROM_NUMBER'] || Rails.application.credentials.dig(:twilio, :from_number) || '+15005550006'
    
    if account_sid.blank? || auth_token.blank?
      redirect_to new_call_path, alert: "Twilio credentials not configured. Please set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN."
      return
    end

    require 'twilio-ruby'
    client = Twilio::REST::Client.new(account_sid, auth_token)
    
    message_url = params[:message_url].presence || 
                  "http://twimlets.com/message?Message%5B0%5D=Hello%2C%20this%20is%20a%20test%20call%20from%20our%20automated%20system.%20Thank%20you%20for%20your%20time.%20Goodbye.&Voice=alice&"
    
    results = []
    
    phone_numbers.each do |phone_number|
      begin
        call = client.calls.create(
          to: phone_number,
          from: from_number,
          url: message_url
        )
        
        Call.create(
          phone_number: phone_number,
          status: call.status,
          sid: call.sid
        )
        
        results << { number: phone_number, status: call.status, success: true }
      rescue Twilio::REST::RestError => e
        Call.create(
          phone_number: phone_number,
          status: 'failed',
          error_message: e.message
        )
        
        results << { number: phone_number, status: 'failed', error: e.message, success: false }
      end
    end
    
    successful = results.count { |r| r[:success] }
    failed = results.count { |r| !r[:success] }
    
    redirect_to calls_path, notice: "Calls initiated: #{successful} successful, #{failed} failed."
  end

  def destroy
    @call = Call.find(params[:id])
    @call.destroy
    redirect_to calls_url, notice: "Call log was successfully deleted."
  end

  def destroy_all
    Call.destroy_all
    redirect_to calls_url, notice: "All call logs cleared."
  end
end

