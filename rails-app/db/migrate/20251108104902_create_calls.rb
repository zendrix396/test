class CreateCalls < ActiveRecord::Migration[8.1]
  def change
    create_table :calls do |t|
      t.string :phone_number
      t.string :status
      t.text :error_message
      t.string :sid

      t.timestamps
    end
  end
end
