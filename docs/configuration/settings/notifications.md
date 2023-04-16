# Notifications

Prowlarr supports pushing notifications to external applications and services.

These are not only for Prowlarr to communicate with the outside world, they can also be useful
for monitoring since the user can be alerted, by a service of their choice, when
some kind of event (or problem) occurs.

## Configuration

##### ::: buildarr_prowlarr.config.settings.notifications.NotificationTriggers
    options:
      members:
        - on_health_issue
        - include_health_warnings
        - on_application_update

## Apprise

##### ::: buildarr_prowlarr.config.settings.notifications.AppriseNotification
    options:
      members:
        - type
        - base_url
        - configuration_key
        - stateless_urls
        - apprise_tags
        - auth_username
        - auth_password

## Boxcar

##### ::: buildarr_prowlarr.config.settings.notifications.BoxcarNotification
    options:
      members:
        - type
        - access_token

## Custom Script

##### ::: buildarr_prowlarr.config.settings.notifications.CustomscriptNotification
    options:
      members:
        - type
        - path

## Discord

##### ::: buildarr_prowlarr.config.settings.notifications.DiscordNotification
    options:
      members:
        - type
        - webhook_url
        - username
        - avatar
        - host
        - on_grab_fields
        - on_import_fields

## Email

##### ::: buildarr_prowlarr.config.settings.notifications.EmailNotification
    options:
      members:
        - type
        - server
        - port
        - use_encryption
        - username
        - password
        - from_address
        - recipient_addresses
        - cc_addresses
        - bcc_addresses

## Gotify

##### ::: buildarr_prowlarr.config.settings.notifications.GotifyNotification
    options:
      members:
        - type
        - server
        - app_token
        - priority

## Join

##### ::: buildarr_prowlarr.config.settings.notifications.JoinNotification
    options:
      members:
        - type
        - api_key
        - device_names
        - priority

## Mailgun

##### ::: buildarr_prowlarr.config.settings.notifications.MailgunNotification
    options:
      members:
        - type
        - api_key
        - use_eu_endpoint
        - from_address
        - sender_domain
        - recipient_addresses

## Notifiarr

##### ::: buildarr_prowlarr.config.settings.notifications.NotifiarrNotification
    options:
      members:
        - type
        - api_key

## ntfy

##### ::: buildarr_prowlarr.config.settings.notifications.NtfyNotification
    options:
      members:
        - type
        - server_url
        - username
        - password
        - priority
        - topics
        - ntfy_tags
        - click_url

## Prowl

##### ::: buildarr_prowlarr.config.settings.notifications.ProwlNotification
    options:
      members:
        - type
        - api_key
        - priority

## Pushbullet

##### ::: buildarr_prowlarr.config.settings.notifications.PushbulletNotification
    options:
      members:
        - type
        - api_key
        - device_ids
        - channel_tags
        - sender_id

## Pushover

##### ::: buildarr_prowlarr.config.settings.notifications.PushoverNotification
    options:
      members:
        - type
        - user_key
        - api_key
        - devices
        - priority
        - retry
        - expire
        - sound

## SendGrid

##### ::: buildarr_prowlarr.config.settings.notifications.SendgridNotification
    options:
      members:
        - type
        - api_key
        - from_address
        - recipient_addresses

## Slack

##### ::: buildarr_prowlarr.config.settings.notifications.SlackNotification
    options:
      members:
        - type
        - webhook_url
        - username
        - icon
        - channel

## Telegram

##### ::: buildarr_prowlarr.config.settings.notifications.TelegramNotification
    options:
      members:
        - type
        - bot_token
        - chat_id
        - send_silently

## Twitter

##### ::: buildarr_prowlarr.config.settings.notifications.TwitterNotification
    options:
      members:
        - type
        - consumer_key
        - consumer_secret
        - access_token
        - access_token_secret
        - mention
        - direct_message

## Webhook

##### ::: buildarr_prowlarr.config.settings.notifications.WebhookNotification
    options:
      members:
        - type
        - webhook_url
        - method
        - username
        - password
