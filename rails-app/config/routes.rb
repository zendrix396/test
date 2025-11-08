Rails.application.routes.draw do
  # Define your application routes per the DSL in https://guides.rubyonrails.org/routing.html

  # Reveal health status on /up that returns 200 if the app boots with no exceptions, otherwise 500.
  # Can be used by load balancers and uptime monitors to verify that the app is live.
  get "up" => "rails/health#show", as: :rails_health_check

  # Render dynamic PWA files from app/views/pwa/* (remember to link manifest in application.html.erb)
  # get "manifest" => "rails/pwa#manifest", as: :pwa_manifest
  # get "service-worker" => "rails/pwa#service_worker", as: :pwa_service_worker

  resources :blogs
  get 'generate_blogs', to: 'blogs#new_generation'
  post 'generate_blogs', to: 'blogs#create_generation'
  post 'generate_blogs/stream', to: 'blogs#stream_generation', as: :stream_generate_blogs
  
  resources :calls, only: [:index, :new, :create, :destroy]
  delete 'calls_clear_all', to: 'calls#destroy_all', as: :clear_all_calls
  
  root 'blogs#index'
end
